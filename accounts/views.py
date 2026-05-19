"""
views.py — Controllers (the C in MVC).
Each view function is a controller: it accepts a request, talks to the
Model layer (via ORM), and returns a response (rendered template or redirect).

Role-based access control is delegated to `permissions.py` — this module
should NOT contain raw `if user.role == ...` checks for resource access.
The only role checks here are for *route entry* (e.g. only patients see
the booking page); per-record decisions go through permissions helpers.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Count, F

from .models import (
    Doctor, Appointment, MedicalRecord, Prescription,
    Department, Drug, DrugStock, Equipment,
)
from .forms import (
    PatientRegistrationForm, AppointmentForm,
    MedicalRecordForm, PrescriptionForm,
    DrugForm, DrugStockForm, EquipmentForm,
)
from . import permissions as perms


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def register_patient(request):
    """USE CASE: Register a new patient account."""
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account is ready.")
            return redirect('dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    """Role-based router after login. Six roles → six destinations."""
    user = request.user
    if user.role == 'PATIENT':
        return redirect('my_appointments')
    if user.role == 'DOCTOR':
        return redirect('doctor_schedule')
    if user.role == 'NURSE':
        return redirect('nurse_prescriptions')
    if user.role == 'PHARMACIST':
        return redirect('drug_stock_list')
    if user.role == 'MANAGEMENT':
        return redirect('management_dashboard')
    return redirect('/admin/')  # admin -> Django admin


# ---------------------------------------------------------------------------
# Patient flows
# ---------------------------------------------------------------------------

@login_required
def doctor_list(request):
    """USE CASE: Patient browses doctors to book.

    Supports two optional filters via querystring:
        ?department=<name>          — exact match on Department.name
        ?specialization=<substring> — case-insensitive substring match

    Both filters are read-only and only narrow the existing queryset; they
    don't grant any additional access.
    """
    if not perms.can_book_appointment(request.user):
        return perms.deny("Only patients may browse doctors for booking.")

    qs = Doctor.objects.select_related('user', 'department').all()

    department = request.GET.get('department', '').strip()
    specialization = request.GET.get('specialization', '').strip()

    if department:
        qs = qs.filter(department__name__iexact=department)
    if specialization:
        qs = qs.filter(specialization__icontains=specialization)

    departments = Department.objects.order_by('name')
    specializations = (Doctor.objects
                       .order_by('specialization')
                       .values_list('specialization', flat=True)
                       .distinct())

    return render(request, 'appointments/doctor_list.html', {
        'doctors': qs,
        'departments': departments,
        'specializations': specializations,
        'selected_department': department,
        'selected_specialization': specialization,
    })


@login_required
def book_appointment(request, doctor_id):
    """USE CASE: Patient books an appointment with a specific doctor."""
    if not perms.can_book_appointment(request.user):
        return perms.deny("Only patients may book appointments.")

    doctor = get_object_or_404(Doctor, pk=doctor_id)

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.patient = request.user.patient_profile
            appt.doctor = doctor
            try:
                appt.save()
            except IntegrityError:
                form.add_error('scheduled_at',
                               "This doctor is already booked at that time.")
            else:
                messages.success(request, "Appointment booked.")
                return redirect('my_appointments')
    else:
        form = AppointmentForm()

    return render(request, 'appointments/book.html',
                  {'form': form, 'doctor': doctor})


@login_required
def my_appointments(request):
    """USE CASE: Patient views their appointment history.

    Patients see appointment metadata only (doctor, time, status). The full
    MedicalRecord (diagnosis/notes/treatment) and Prescriptions are NOT
    exposed here — that decision lives in permissions.can_view_medical_record.
    """
    if request.user.role != 'PATIENT':
        return perms.deny("Patients only.")

    appts = (Appointment.objects
             .filter(patient=request.user.patient_profile)
             .select_related('doctor__user', 'doctor__department'))
    return render(request, 'appointments/my_appointments.html',
                  {'appointments': appts})


# ---------------------------------------------------------------------------
# Doctor flows
# ---------------------------------------------------------------------------

@login_required
def doctor_schedule(request):
    """USE CASE: Doctor views their schedule."""
    if request.user.role != 'DOCTOR':
        return perms.deny("Doctors only.")

    appts = (Appointment.objects
             .filter(doctor=request.user.doctor_profile)
             .select_related('patient__user'))
    return render(request, 'appointments/doctor_schedule.html',
                  {'appointments': appts})


@login_required
def add_medical_record(request, appointment_id):
    """USE CASE: Doctor records diagnosis/notes/treatment for an appointment."""
    appointment = get_object_or_404(Appointment, pk=appointment_id)

    if not perms.can_write_medical_record(request.user, appointment):
        return perms.deny("Only the assigned doctor may record this visit.")

    # If a record already exists, don't allow duplicate
    if hasattr(appointment, 'medical_record'):
        messages.info(request, "Medical record already exists for this appointment.")
        return redirect('doctor_schedule')

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.appointment = appointment
            record.save()

            # Lifecycle transition: appointment is now COMPLETED
            appointment.status = 'COMPLETED'
            appointment.save(update_fields=['status'])

            messages.success(request, "Medical record saved. You can now add prescriptions.")
            return redirect('add_prescription', record_id=record.id)
    else:
        form = MedicalRecordForm()

    return render(request, 'appointments/add_record.html',
                  {'form': form, 'appointment': appointment})


@login_required
def add_prescription(request, record_id):
    """USE CASE: Doctor prescribes a medication tied to a MedicalRecord.

    Only the doctor who authored the record may prescribe against it
    (enforced via perms.can_write_prescription). Nurses cannot reach
    this URL even with the link — they get a 403.
    """
    record = get_object_or_404(MedicalRecord, pk=record_id)

    if not perms.can_write_prescription(request.user, record):
        return perms.deny("Only the prescribing doctor may add prescriptions.")

    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            rx = form.save(commit=False)
            rx.medical_record = record
            rx.save()
            messages.success(request, f"Prescribed {rx.drug_name}.")
            # Stay on the same page so the doctor can prescribe multiple drugs
            return redirect('add_prescription', record_id=record.id)
    else:
        form = PrescriptionForm()

    existing = record.prescriptions.all()
    return render(request, 'appointments/add_prescription.html',
                  {'form': form, 'record': record, 'prescriptions': existing})


# ---------------------------------------------------------------------------
# Nurse flows (read-only, scoped to the nurse's department)
# ---------------------------------------------------------------------------

@login_required
def nurse_prescriptions(request):
    """USE CASE: Nurse views prescriptions for patients in their department.

    Nurses see drug name, dosage, frequency, duration, the prescribing doctor,
    and the diagnosis the prescription is tied to. They CANNOT edit, delete,
    or create prescriptions — that is reserved for the prescribing Doctor.
    """
    if request.user.role != 'NURSE':
        return perms.deny("Nurses only.")

    nurse = request.user.nurse_profile
    rxs = (Prescription.objects
           .filter(medical_record__appointment__doctor__department=nurse.department)
           .select_related(
               'medical_record__appointment__doctor__user',
               'medical_record__appointment__patient__user',
           )
           .order_by('-created_at'))
    return render(request, 'accounts/nurse_prescriptions.html',
                  {'prescriptions': rxs, 'nurse': nurse})


# ---------------------------------------------------------------------------
# Pharmacist flows (drug catalog + stock management, hospital-wide)
# ---------------------------------------------------------------------------

@login_required
def drug_catalog(request):
    """USE CASE: Pharmacist manages the master Drug catalog (read for all
    non-patient roles, write for Pharmacist/Admin)."""
    if not perms.can_view_drug_catalog(request.user):
        return perms.deny("Drug catalog is not available to patients.")

    drugs = Drug.objects.all()
    return render(request, 'pharmacy/drug_catalog.html', {'drugs': drugs})


@login_required
def drug_create(request):
    """USE CASE: Pharmacist adds a new drug to the catalog."""
    if not perms.can_write_drug_catalog(request.user):
        return perms.deny("Only the pharmacist may edit the drug catalog.")

    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            drug = form.save()
            messages.success(request, f"Added '{drug.name}' to the catalog.")
            return redirect('drug_catalog')
    else:
        form = DrugForm()
    return render(request, 'pharmacy/drug_form.html', {'form': form})


@login_required
def drug_stock_list(request):
    """USE CASE: View drug stock.

    - Pharmacist / Management / Admin see all departments.
    - Doctor / Nurse see only their department's stock.
    Visibility is enforced by querying with a department filter for clinical
    roles, plus a per-row permission check (defense in depth).
    """
    user = request.user
    qs = DrugStock.objects.select_related('drug', 'department')

    if user.role == 'DOCTOR':
        qs = qs.filter(department=user.doctor_profile.department)
    elif user.role == 'NURSE':
        qs = qs.filter(department=user.nurse_profile.department)
    elif user.role in ('PHARMACIST', 'MANAGEMENT', 'ADMIN') or user.is_superuser:
        pass  # full hospital-wide view
    else:
        return perms.deny("Drug stock is not available to your role.")

    can_adjust = perms.can_write_drug_stock(user)
    return render(request, 'pharmacy/stock_list.html',
                  {'stock': qs, 'can_adjust': can_adjust})


@login_required
def drug_stock_adjust(request, stock_id):
    """USE CASE: Pharmacist updates a stock row (quantity, reorder level, expiry)."""
    if not perms.can_write_drug_stock(request.user):
        return perms.deny("Only the pharmacist may adjust drug stock.")

    stock = get_object_or_404(DrugStock, pk=stock_id)

    if request.method == 'POST':
        form = DrugStockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated stock for {stock.drug.name}.")
            return redirect('drug_stock_list')
    else:
        form = DrugStockForm(instance=stock)
    return render(request, 'pharmacy/stock_adjust.html',
                  {'form': form, 'stock': stock})


# ---------------------------------------------------------------------------
# Equipment flows
# ---------------------------------------------------------------------------

@login_required
def equipment_list(request):
    """USE CASE: Browse equipment.

    Doctor / Nurse: own department only. Management / Admin: hospital-wide.
    Pharmacist and Patient: 403 (not their concern).
    """
    user = request.user
    qs = Equipment.objects.select_related('department')

    if user.role == 'DOCTOR':
        qs = qs.filter(department=user.doctor_profile.department)
    elif user.role == 'NURSE':
        qs = qs.filter(department=user.nurse_profile.department)
    elif user.role in ('MANAGEMENT', 'ADMIN') or user.is_superuser:
        pass
    else:
        return perms.deny("Equipment list is not available to your role.")

    can_edit = perms.can_write_equipment(user)
    return render(request, 'equipment/list.html',
                  {'equipment': qs, 'can_edit': can_edit})


@login_required
def equipment_edit(request, equipment_id):
    """USE CASE: Management updates equipment status / service date."""
    if not perms.can_write_equipment(request.user):
        return perms.deny("Only management may update equipment status.")

    equipment = get_object_or_404(Equipment, pk=equipment_id)

    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {equipment.name}.")
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'equipment/edit.html',
                  {'form': form, 'equipment': equipment})


# ---------------------------------------------------------------------------
# Management dashboard (read-only operational KPIs)
# ---------------------------------------------------------------------------

@login_required
def management_dashboard(request):
    """USE CASE: Management views aggregate operational KPIs.

    Read-only across the hospital: low-stock drugs, equipment status counts,
    appointment volume by department. No PHI (no patient names, no
    diagnoses) — management oversees operations, not clinical content.
    """
    if not perms.can_view_management_dashboard(request.user):
        return perms.deny("Management dashboard is restricted.")

    low_stock = (DrugStock.objects
                 .select_related('drug', 'department')
                 .filter(quantity__lte=F('reorder_level'))
                 .order_by('quantity'))

    equipment_by_status = (Equipment.objects
                           .values('status')
                           .annotate(n=Count('id'))
                           .order_by('status'))

    appts_by_dept = (Appointment.objects
                     .values('doctor__department__name')
                     .annotate(n=Count('id'))
                     .order_by('-n'))

    return render(request, 'management/dashboard.html', {
        'low_stock': low_stock,
        'equipment_by_status': equipment_by_status,
        'appts_by_dept': appts_by_dept,
    })
