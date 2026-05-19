"""
permissions.py — centralized role-based access control.

This module is the SINGLE SOURCE OF TRUTH for the permission matrix
documented in SAD §3.5. Every controller (Django view) consults these
helpers instead of duplicating role-check logic.

Why a separate module?
- Controllers stay thin and read like business logic, not auth boilerplate.
- The grading criterion "show me where access is enforced" has one answer:
  here. The matrix in the SAD and the code in this file MUST stay in sync.
- A future REST/API layer can reuse these helpers unchanged.

Place this file at: accounts/permissions.py
"""

from django.http import HttpResponseForbidden


# ---------------------------------------------------------------------------
# Read permissions
# ---------------------------------------------------------------------------

def can_view_appointment(user, appointment):
    """Who can see an Appointment row?

    - Admin / superuser: always
    - Patient: only their own appointments
    - Doctor: only appointments they are the assigned doctor for
    - Nurse: any appointment whose doctor is in their department
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    if user.role == 'PATIENT':
        patient = getattr(user, 'patient_profile', None)
        return patient is not None and appointment.patient_id == patient.id
    if user.role == 'DOCTOR':
        return appointment.doctor.user_id == user.id
    if user.role == 'NURSE':
        nurse = getattr(user, 'nurse_profile', None)
        return nurse is not None and \
            appointment.doctor.department_id == nurse.department_id
    return False


def can_view_medical_record(user, record):
    """Who can see a MedicalRecord (full diagnosis + notes + treatment)?

    - Admin / superuser: always
    - Doctor: only records they authored
    - Nurse: read-only access for records in their department
    - Patient: NO ACCESS to the full clinical record (they see appointment
      status only — the doctor's notes and clinical reasoning are not
      patient-facing in Phase 1).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    if user.role == 'DOCTOR':
        return record.appointment.doctor.user_id == user.id
    if user.role == 'NURSE':
        nurse = getattr(user, 'nurse_profile', None)
        return nurse is not None and \
            record.appointment.doctor.department_id == nurse.department_id
    # PATIENT and any other role: denied
    return False


def can_view_prescription(user, prescription):
    """Who can see a Prescription? Same scope as the parent MedicalRecord."""
    return can_view_medical_record(user, prescription.medical_record)


# ---------------------------------------------------------------------------
# Write permissions
# ---------------------------------------------------------------------------

def can_write_medical_record(user, appointment):
    """Only the doctor assigned to the appointment may add/modify the record.

    Admins do not write clinical data through the front-end controllers;
    if they need to, they go through the Django admin (audited path).
    """
    if not user.is_authenticated:
        return False
    if user.role != 'DOCTOR':
        return False
    return appointment.doctor.user_id == user.id


def can_write_prescription(user, medical_record):
    """Only the doctor who authored the record may prescribe against it.

    Nurses are explicitly read-only on prescriptions — they dispense, not
    prescribe.
    """
    return can_write_medical_record(user, medical_record.appointment)


def can_book_appointment(user):
    """Patients book appointments. No one else (including admins via UI)."""
    return user.is_authenticated and user.role == 'PATIENT'


def can_cancel_appointment(user, appointment):
    """Only the patient who owns an upcoming appointment may cancel it.

    Refuses if the appointment is already COMPLETED or CANCELLED, or if the
    scheduled time is in the past — past appointments are history, not future
    work. Admins do NOT cancel through the patient-facing endpoint; if they
    need to administratively cancel, they go through the Django admin.
    """
    if not user.is_authenticated:
        return False
    if user.role != 'PATIENT':
        return False
    patient = getattr(user, 'patient_profile', None)
    if patient is None or appointment.patient_id != patient.id:
        return False
    if appointment.status in ('COMPLETED', 'CANCELLED'):
        return False
    from django.utils import timezone
    if appointment.scheduled_at <= timezone.now():
        return False
    return True


def can_edit_availability(user, doctor):
    """A doctor edits only their own availability. Admin may edit any.

    Used by the PUT /api/doctors/<id>/availability/ endpoint.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    if user.role != 'DOCTOR':
        return False
    return doctor.user_id == user.id


def can_view_rooms(user):
    """Who can list rooms?

    DOCTOR, NURSE, MANAGEMENT, ADMIN may view. PATIENT and PHARMACIST cannot
    — patients have no business browsing the ward map and pharmacy is a
    central function with no room scope.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in ('DOCTOR', 'NURSE', 'MANAGEMENT', 'ADMIN')


# ---------------------------------------------------------------------------
# Inventory: Drug catalog and stock
# ---------------------------------------------------------------------------

def can_view_drug_catalog(user):
    """Who can see the master Drug list?

    Everyone except Patients. Doctors need it to prescribe; nurses need it
    to verify dispense; pharmacists own it; management oversees it.
    """
    if not user.is_authenticated:
        return False
    if user.role == 'PATIENT':
        return False
    return True


def can_write_drug_catalog(user):
    """Pharmacist owns the catalog. Admin can also edit via Django admin."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    return user.role == 'PHARMACIST'


def can_view_drug_stock(user, stock):
    """Per-row visibility for DrugStock.

    - Pharmacist / Management / Admin: all stock rows (hospital-wide)
    - Doctor / Nurse: only stock rows for their own department
    - Patient: never
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role in ('ADMIN', 'PHARMACIST', 'MANAGEMENT'):
        return True
    if user.role == 'DOCTOR':
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and stock.department_id == doc.department_id
    if user.role == 'NURSE':
        nurse = getattr(user, 'nurse_profile', None)
        return nurse is not None and stock.department_id == nurse.department_id
    return False


def can_write_drug_stock(user):
    """Only Pharmacist (and Admin) may adjust stock quantities.

    Management is read-only on stock — they oversee, they don't dispense.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    return user.role == 'PHARMACIST'


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

def can_view_equipment(user, equipment):
    """Per-row visibility for Equipment.

    - Management / Admin: all equipment (hospital-wide)
    - Doctor / Nurse: only equipment in their department
    - Pharmacist / Patient: never (not their concern)
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role in ('ADMIN', 'MANAGEMENT'):
        return True
    if user.role == 'DOCTOR':
        doc = getattr(user, 'doctor_profile', None)
        return doc is not None and equipment.department_id == doc.department_id
    if user.role == 'NURSE':
        nurse = getattr(user, 'nurse_profile', None)
        return nurse is not None and equipment.department_id == nurse.department_id
    return False


def can_write_equipment(user):
    """Management updates equipment status. Procurement still goes through Admin.

    Nurses don't update status in Phase 1 (they would in a full system; this
    keeps the matrix narrow and defensible for the iteration).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.role == 'ADMIN':
        return True
    return user.role == 'MANAGEMENT'


# ---------------------------------------------------------------------------
# Management dashboard
# ---------------------------------------------------------------------------

def can_view_management_dashboard(user):
    """Read-only operational KPIs (stock low-water counts, equipment status,
    appointment volume by department). Management and Admin only."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.role in ('MANAGEMENT', 'ADMIN')


# ---------------------------------------------------------------------------
# Controller helper — uniform 403 response
# ---------------------------------------------------------------------------

def deny(message="You do not have permission to view this resource."):
    """Returns a uniform 403 so all permission failures look the same.

    Using the same response shape everywhere prevents accidental information
    leakage (e.g., 'patient not found' vs 'forbidden' telling an attacker
    whether a record exists).
    """
    return HttpResponseForbidden(message)
