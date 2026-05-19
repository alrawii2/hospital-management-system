"""
tests.py — Automated verification of the §3.5 Permission Matrix.

Place at: accounts/tests.py
Run with: python manage.py test accounts

These tests are the second half of the security story:
  - SAD §3.5 documents the matrix as an architectural artifact.
  - accounts/permissions.py implements the matrix as code.
  - accounts/tests.py (this file) PROVES the implementation matches the doc.

Two layers of coverage:
  1. PermissionUnitTests — direct calls to perms.*; fast, no HTTP.
  2. HttpAccessTests      — Django test Client; round-trips a real request through
                            URL → Controller → Permissions → ORM and asserts the
                            response status. Catches misconfigured URL routing
                            and missing permission checks.

A failing test here means the implementation has drifted from §3.5.
"""

from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    User, Patient, Doctor, Nurse, Pharmacist, Manager,
    Department, Appointment, MedicalRecord, Prescription,
    Drug, DrugStock, Equipment,
    DoctorAvailability, Room,
)
from accounts import permissions as perms


# ---------------------------------------------------------------------------
# Shared fixture base class
# ---------------------------------------------------------------------------

class HospitalTestBase(TestCase):
    """One user per role, two of each clinical role to test department scope."""

    @classmethod
    def setUpTestData(cls):
        # Departments
        cls.cardio = Department.objects.create(name="Cardiology")
        cls.peds = Department.objects.create(name="Pediatrics")

        # Admin (superuser)
        cls.admin = User.objects.create_superuser(
            username='admin1', email='a@h.demo', password='pass',
            role='ADMIN',
        )

        # Two doctors in different departments — to verify "own pts" scope
        cls.doc_cardio = cls._make_user('doc_c', 'DOCTOR')
        cls.doc_cardio_p = Doctor.objects.create(
            user=cls.doc_cardio, department=cls.cardio,
            specialization='Cardiologist', license_number='MD-1',
            years_of_experience=10,
        )
        cls.doc_peds = cls._make_user('doc_p', 'DOCTOR')
        cls.doc_peds_p = Doctor.objects.create(
            user=cls.doc_peds, department=cls.peds,
            specialization='Pediatrician', license_number='MD-2',
            years_of_experience=8,
        )

        # Two nurses, one per department — to verify dept scope
        cls.nurse_cardio = cls._make_user('nurse_c', 'NURSE')
        cls.nurse_cardio_p = Nurse.objects.create(
            user=cls.nurse_cardio, department=cls.cardio,
            license_number='RN-1', shift='DAY',
        )
        cls.nurse_peds = cls._make_user('nurse_p', 'NURSE')
        cls.nurse_peds_p = Nurse.objects.create(
            user=cls.nurse_peds, department=cls.peds,
            license_number='RN-2', shift='DAY',
        )

        # Hospital-wide roles (no department scope)
        cls.pharmacist = cls._make_user('pharma', 'PHARMACIST')
        Pharmacist.objects.create(user=cls.pharmacist, license_number='PH-1')

        cls.manager = cls._make_user('manager', 'MANAGEMENT')
        Manager.objects.create(user=cls.manager, title='Operations Manager')

        # Two patients
        cls.patient = cls._make_user('pt1', 'PATIENT')
        cls.patient_p = Patient.objects.create(
            user=cls.patient, date_of_birth=date(1990, 1, 1),
            gender='F', blood_type='A+',
        )
        cls.other_patient = cls._make_user('pt2', 'PATIENT')
        cls.other_patient_p = Patient.objects.create(
            user=cls.other_patient, date_of_birth=date(1985, 1, 1),
            gender='M', blood_type='O+',
        )

        # Domain objects: an appointment in Cardiology with a record + Rx
        cls.appt = Appointment.objects.create(
            patient=cls.patient_p, doctor=cls.doc_cardio_p,
            scheduled_at=timezone.now() + timedelta(days=2),
            reason='Test', status='CONFIRMED',
        )
        cls.record = MedicalRecord.objects.create(
            appointment=cls.appt, diagnosis='Test dx',
            notes='Test notes', treatment='Test treatment',
        )
        cls.drug = Drug.objects.create(name='TestDrug', category='ANALGESIC')
        cls.rx = Prescription.objects.create(
            medical_record=cls.record, drug=cls.drug,
            drug_name='TestDrug', dosage='10 mg',
            frequency='daily', duration='7 days',
        )
        # Stock: low in Pediatrics, healthy in Cardiology
        cls.cardio_stock = DrugStock.objects.create(
            drug=cls.drug, department=cls.cardio,
            quantity=50, reorder_level=10,
        )
        cls.peds_stock = DrugStock.objects.create(
            drug=cls.drug, department=cls.peds,
            quantity=8, reorder_level=10,
        )
        # One equipment item per department
        cls.cardio_equip = Equipment.objects.create(
            name='ECG', serial_number='ECG-1', department=cls.cardio,
        )
        cls.peds_equip = Equipment.objects.create(
            name='Incubator', serial_number='INC-1', department=cls.peds,
        )

    @staticmethod
    def _make_user(username, role):
        u = User.objects.create_user(
            username=username, email=f'{username}@h.demo', password='pass',
            role=role,
        )
        return u


# ---------------------------------------------------------------------------
# Layer 1 — Permission helper unit tests (pure functions, no HTTP)
# ---------------------------------------------------------------------------

class PermissionUnitTests(HospitalTestBase):
    """Each test maps to one or more cells of §3.5."""

    # --- can_book_appointment ---
    def test_only_patient_can_book(self):
        self.assertTrue(perms.can_book_appointment(self.patient))
        for u in [self.doc_cardio, self.nurse_cardio, self.pharmacist,
                  self.manager]:
            self.assertFalse(perms.can_book_appointment(u))

    # --- can_view_appointment ---
    def test_patient_sees_own_appointment(self):
        self.assertTrue(perms.can_view_appointment(self.patient, self.appt))

    def test_patient_cannot_see_other_patient_appointment(self):
        self.assertFalse(perms.can_view_appointment(self.other_patient, self.appt))

    def test_doctor_sees_own_appointment(self):
        self.assertTrue(perms.can_view_appointment(self.doc_cardio, self.appt))

    def test_doctor_cannot_see_other_doctors_appointment(self):
        self.assertFalse(perms.can_view_appointment(self.doc_peds, self.appt))

    def test_nurse_sees_dept_appointment(self):
        self.assertTrue(perms.can_view_appointment(self.nurse_cardio, self.appt))

    def test_nurse_cannot_see_other_dept_appointment(self):
        self.assertFalse(perms.can_view_appointment(self.nurse_peds, self.appt))

    def test_pharmacist_cannot_see_appointment(self):
        self.assertFalse(perms.can_view_appointment(self.pharmacist, self.appt))

    def test_admin_sees_appointment(self):
        self.assertTrue(perms.can_view_appointment(self.admin, self.appt))

    # --- can_view_medical_record ---
    def test_patient_blocked_from_medical_record(self):
        self.assertFalse(perms.can_view_medical_record(self.patient, self.record))

    def test_doctor_sees_own_medical_record(self):
        self.assertTrue(perms.can_view_medical_record(self.doc_cardio, self.record))

    def test_doctor_cannot_see_other_doctors_medical_record(self):
        self.assertFalse(perms.can_view_medical_record(self.doc_peds, self.record))

    def test_nurse_sees_dept_medical_record(self):
        self.assertTrue(perms.can_view_medical_record(self.nurse_cardio, self.record))

    def test_nurse_cannot_see_other_dept_medical_record(self):
        self.assertFalse(perms.can_view_medical_record(self.nurse_peds, self.record))

    # --- can_write_medical_record ---
    def test_only_assigned_doctor_writes_medical_record(self):
        self.assertTrue(perms.can_write_medical_record(self.doc_cardio, self.appt))
        self.assertFalse(perms.can_write_medical_record(self.doc_peds, self.appt))
        self.assertFalse(perms.can_write_medical_record(self.nurse_cardio, self.appt))
        self.assertFalse(perms.can_write_medical_record(self.patient, self.appt))

    # --- can_view / can_write_prescription ---
    def test_prescription_visibility_follows_medical_record(self):
        self.assertTrue(perms.can_view_prescription(self.doc_cardio, self.rx))
        self.assertTrue(perms.can_view_prescription(self.nurse_cardio, self.rx))
        self.assertFalse(perms.can_view_prescription(self.nurse_peds, self.rx))
        self.assertFalse(perms.can_view_prescription(self.patient, self.rx))

    def test_only_owning_doctor_writes_prescription(self):
        self.assertTrue(perms.can_write_prescription(self.doc_cardio, self.record))
        self.assertFalse(perms.can_write_prescription(self.doc_peds, self.record))
        self.assertFalse(perms.can_write_prescription(self.pharmacist, self.record))

    # --- Drug catalog ---
    def test_drug_catalog_read_for_all_non_patient(self):
        for u in [self.doc_cardio, self.nurse_cardio, self.pharmacist,
                  self.manager, self.admin]:
            self.assertTrue(perms.can_view_drug_catalog(u),
                            f"{u.role} should read drug catalog")
        self.assertFalse(perms.can_view_drug_catalog(self.patient))

    def test_drug_catalog_write_only_pharmacist_and_admin(self):
        self.assertTrue(perms.can_write_drug_catalog(self.pharmacist))
        self.assertTrue(perms.can_write_drug_catalog(self.admin))
        for u in [self.doc_cardio, self.nurse_cardio, self.manager, self.patient]:
            self.assertFalse(perms.can_write_drug_catalog(u))

    # --- Drug stock ---
    def test_drug_stock_view_dept_scope(self):
        # Doctor in Cardiology sees Cardiology stock, not Pediatrics
        self.assertTrue(perms.can_view_drug_stock(self.doc_cardio, self.cardio_stock))
        self.assertFalse(perms.can_view_drug_stock(self.doc_cardio, self.peds_stock))
        # Nurse same rule
        self.assertTrue(perms.can_view_drug_stock(self.nurse_cardio, self.cardio_stock))
        self.assertFalse(perms.can_view_drug_stock(self.nurse_cardio, self.peds_stock))
        # Pharmacist + management see all
        for u in [self.pharmacist, self.manager, self.admin]:
            self.assertTrue(perms.can_view_drug_stock(u, self.cardio_stock))
            self.assertTrue(perms.can_view_drug_stock(u, self.peds_stock))
        # Patient never
        self.assertFalse(perms.can_view_drug_stock(self.patient, self.cardio_stock))

    def test_drug_stock_write_only_pharmacist_and_admin(self):
        self.assertTrue(perms.can_write_drug_stock(self.pharmacist))
        self.assertTrue(perms.can_write_drug_stock(self.admin))
        for u in [self.doc_cardio, self.nurse_cardio, self.manager, self.patient]:
            self.assertFalse(perms.can_write_drug_stock(u))

    # --- Equipment ---
    def test_equipment_view_dept_scope(self):
        # Doctor + Nurse: own dept only
        self.assertTrue(perms.can_view_equipment(self.doc_cardio, self.cardio_equip))
        self.assertFalse(perms.can_view_equipment(self.doc_cardio, self.peds_equip))
        self.assertTrue(perms.can_view_equipment(self.nurse_cardio, self.cardio_equip))
        self.assertFalse(perms.can_view_equipment(self.nurse_cardio, self.peds_equip))
        # Management + Admin: all
        for u in [self.manager, self.admin]:
            self.assertTrue(perms.can_view_equipment(u, self.cardio_equip))
            self.assertTrue(perms.can_view_equipment(u, self.peds_equip))
        # Pharmacist + Patient: never
        for u in [self.pharmacist, self.patient]:
            self.assertFalse(perms.can_view_equipment(u, self.cardio_equip))

    def test_equipment_write_only_management_and_admin(self):
        self.assertTrue(perms.can_write_equipment(self.manager))
        self.assertTrue(perms.can_write_equipment(self.admin))
        for u in [self.doc_cardio, self.nurse_cardio, self.pharmacist, self.patient]:
            self.assertFalse(perms.can_write_equipment(u))

    # --- Phase 2.1: cancel appointment ---
    def test_only_owning_patient_can_cancel_upcoming(self):
        self.assertTrue(perms.can_cancel_appointment(self.patient, self.appt))
        # Other patient — not theirs
        self.assertFalse(perms.can_cancel_appointment(self.other_patient, self.appt))
        # Doctor / nurse / admin — never via the patient endpoint
        for u in [self.doc_cardio, self.nurse_cardio, self.admin, self.manager]:
            self.assertFalse(perms.can_cancel_appointment(u, self.appt))

    def test_cannot_cancel_completed_or_cancelled(self):
        self.appt.status = 'COMPLETED'
        self.appt.save()
        self.assertFalse(perms.can_cancel_appointment(self.patient, self.appt))
        self.appt.status = 'CANCELLED'
        self.appt.save()
        self.assertFalse(perms.can_cancel_appointment(self.patient, self.appt))

    def test_cannot_cancel_past_appointment(self):
        self.appt.status = 'CONFIRMED'
        self.appt.scheduled_at = timezone.now() - timedelta(hours=1)
        self.appt.save()
        self.assertFalse(perms.can_cancel_appointment(self.patient, self.appt))

    # --- Phase 2.1: availability ---
    def test_doctor_can_edit_own_availability_admin_too(self):
        self.assertTrue(perms.can_edit_availability(self.doc_cardio, self.doc_cardio_p))
        self.assertTrue(perms.can_edit_availability(self.admin, self.doc_cardio_p))
        # Other doctor cannot edit
        self.assertFalse(perms.can_edit_availability(self.doc_peds, self.doc_cardio_p))
        # Nurse / pharmacist / patient / manager cannot edit doctor's schedule
        for u in [self.nurse_cardio, self.pharmacist, self.patient, self.manager]:
            self.assertFalse(perms.can_edit_availability(u, self.doc_cardio_p))

    # --- Phase 2.1: room visibility ---
    def test_room_view_matrix(self):
        for u in [self.doc_cardio, self.nurse_cardio, self.manager, self.admin]:
            self.assertTrue(perms.can_view_rooms(u),
                            f"{u.role} should see rooms")
        for u in [self.patient, self.pharmacist]:
            self.assertFalse(perms.can_view_rooms(u),
                             f"{u.role} should NOT see rooms")

    # --- Management dashboard ---
    def test_management_dashboard_only_management_and_admin(self):
        self.assertTrue(perms.can_view_management_dashboard(self.manager))
        self.assertTrue(perms.can_view_management_dashboard(self.admin))
        for u in [self.doc_cardio, self.nurse_cardio, self.pharmacist, self.patient]:
            self.assertFalse(perms.can_view_management_dashboard(u))


# ---------------------------------------------------------------------------
# Layer 2 — HTTP integration tests (Django test Client)
# ---------------------------------------------------------------------------

class HttpAccessTests(HospitalTestBase):
    """End-to-end: real URL → real Controller → real Permissions → real ORM.

    Asserts response.status_code only (templates are placeholders in Phase 1
    and may be empty). 200 = OK, 302 = redirect (e.g. unauthenticated → login),
    403 = permission denied.
    """

    def setUp(self):
        self.c = Client()

    def login(self, user):
        self.c.force_login(user)

    # --- /pharmacy/stock/ list ---
    def test_pharmacy_stock_pharmacist_200(self):
        self.login(self.pharmacist)
        r = self.c.get('/pharmacy/stock/')
        self.assertEqual(r.status_code, 200)

    def test_pharmacy_stock_doctor_200_dept_scoped(self):
        self.login(self.doc_cardio)
        r = self.c.get('/pharmacy/stock/')
        self.assertEqual(r.status_code, 200)
        # Verify queryset is dept-filtered: only Cardiology rows
        stock_in_response = list(r.context['stock'])
        self.assertEqual(len(stock_in_response), 1)
        self.assertEqual(stock_in_response[0].department, self.cardio)

    def test_pharmacy_stock_patient_403(self):
        self.login(self.patient)
        r = self.c.get('/pharmacy/stock/')
        self.assertEqual(r.status_code, 403)

    # --- /pharmacy/drugs/new/ ---
    def test_drug_create_pharmacist_200(self):
        self.login(self.pharmacist)
        r = self.c.get('/pharmacy/drugs/new/')
        self.assertEqual(r.status_code, 200)

    def test_drug_create_doctor_403(self):
        self.login(self.doc_cardio)
        r = self.c.get('/pharmacy/drugs/new/')
        self.assertEqual(r.status_code, 403)

    def test_drug_create_nurse_403(self):
        self.login(self.nurse_cardio)
        r = self.c.get('/pharmacy/drugs/new/')
        self.assertEqual(r.status_code, 403)

    # --- /pharmacy/stock/<id>/adjust/ ---
    def test_stock_adjust_pharmacist_200(self):
        self.login(self.pharmacist)
        r = self.c.get(f'/pharmacy/stock/{self.cardio_stock.id}/adjust/')
        self.assertEqual(r.status_code, 200)

    def test_stock_adjust_nurse_403(self):
        self.login(self.nurse_cardio)
        r = self.c.get(f'/pharmacy/stock/{self.cardio_stock.id}/adjust/')
        self.assertEqual(r.status_code, 403)

    def test_stock_adjust_management_403(self):
        # Management is read-only on stock (matrix §3.5)
        self.login(self.manager)
        r = self.c.get(f'/pharmacy/stock/{self.cardio_stock.id}/adjust/')
        self.assertEqual(r.status_code, 403)

    # --- /management/ dashboard ---
    def test_management_dashboard_manager_200(self):
        self.login(self.manager)
        r = self.c.get('/management/')
        self.assertEqual(r.status_code, 200)

    def test_management_dashboard_pharmacist_403(self):
        self.login(self.pharmacist)
        r = self.c.get('/management/')
        self.assertEqual(r.status_code, 403)

    def test_management_dashboard_doctor_403(self):
        self.login(self.doc_cardio)
        r = self.c.get('/management/')
        self.assertEqual(r.status_code, 403)

    # --- /equipment/ ---
    def test_equipment_pharmacist_403(self):
        self.login(self.pharmacist)
        r = self.c.get('/equipment/')
        self.assertEqual(r.status_code, 403)

    def test_equipment_management_200_all_rows(self):
        self.login(self.manager)
        r = self.c.get('/equipment/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(list(r.context['equipment'])), 2)  # both depts

    def test_equipment_doctor_200_dept_scoped(self):
        self.login(self.doc_cardio)
        r = self.c.get('/equipment/')
        self.assertEqual(r.status_code, 200)
        equipment = list(r.context['equipment'])
        self.assertEqual(len(equipment), 1)
        self.assertEqual(equipment[0].department, self.cardio)

    # --- /nurse/prescriptions/ ---
    def test_nurse_prescriptions_nurse_200_dept_scoped(self):
        self.login(self.nurse_cardio)
        r = self.c.get('/nurse/prescriptions/')
        self.assertEqual(r.status_code, 200)

    def test_nurse_prescriptions_doctor_403(self):
        self.login(self.doc_cardio)
        r = self.c.get('/nurse/prescriptions/')
        self.assertEqual(r.status_code, 403)

    def test_nurse_prescriptions_other_dept_nurse_sees_no_rows(self):
        # Pediatrics nurse should see zero prescriptions (the only Rx is in Cardiology)
        self.login(self.nurse_peds)
        r = self.c.get('/nurse/prescriptions/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(list(r.context['prescriptions'])), 0)

    # --- /appointments/my/ ---
    def test_my_appointments_patient_200_own_only(self):
        self.login(self.patient)
        r = self.c.get('/appointments/my/')
        self.assertEqual(r.status_code, 200)
        # patient1 has the seeded appt; other_patient should not see it
        self.login(self.other_patient)
        r2 = self.c.get('/appointments/my/')
        self.assertEqual(len(list(r2.context['appointments'])), 0)

    # --- Doctor browse filter (the new feature) ---
    def test_doctor_list_unfiltered_returns_all(self):
        self.login(self.patient)
        r = self.c.get('/appointments/doctors/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(list(r.context['doctors'])), 2)

    def test_doctor_list_filtered_by_department(self):
        self.login(self.patient)
        r = self.c.get('/appointments/doctors/?department=Cardiology')
        self.assertEqual(r.status_code, 200)
        doctors = list(r.context['doctors'])
        self.assertEqual(len(doctors), 1)
        self.assertEqual(doctors[0].department, self.cardio)

    def test_doctor_list_filtered_by_specialization(self):
        self.login(self.patient)
        r = self.c.get('/appointments/doctors/?specialization=Pediatric')
        self.assertEqual(r.status_code, 200)
        doctors = list(r.context['doctors'])
        self.assertEqual(len(doctors), 1)
        self.assertEqual(doctors[0].specialization, 'Pediatrician')

    # --- Phase 2.1: REST endpoints ---
    def test_cancel_endpoint_happy_path(self):
        from rest_framework.authtoken.models import Token
        tok, _ = Token.objects.get_or_create(user=self.patient)
        r = self.c.post(
            f'/api/appointments/{self.appt.id}/cancel/',
            HTTP_AUTHORIZATION=f'Token {tok.key}',
        )
        self.assertEqual(r.status_code, 200)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, 'CANCELLED')

    def test_cancel_endpoint_refuses_other_patient(self):
        from rest_framework.authtoken.models import Token
        tok, _ = Token.objects.get_or_create(user=self.other_patient)
        r = self.c.post(
            f'/api/appointments/{self.appt.id}/cancel/',
            HTTP_AUTHORIZATION=f'Token {tok.key}',
        )
        self.assertEqual(r.status_code, 403)
        self.appt.refresh_from_db()
        self.assertEqual(self.appt.status, 'CONFIRMED')

    def test_availability_get_returns_doctor_rows(self):
        DoctorAvailability.objects.create(
            doctor=self.doc_cardio_p, weekday=0,
            start_time='09:00', end_time='12:00', slot_minutes=30,
        )
        from rest_framework.authtoken.models import Token
        tok, _ = Token.objects.get_or_create(user=self.patient)
        r = self.c.get(
            f'/api/doctors/{self.doc_cardio_p.id}/availability/',
            HTTP_AUTHORIZATION=f'Token {tok.key}',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

    def test_availability_put_doctor_only(self):
        from rest_framework.authtoken.models import Token
        import json
        # Wrong doctor cannot edit
        tok, _ = Token.objects.get_or_create(user=self.doc_peds)
        r = self.c.put(
            f'/api/doctors/{self.doc_cardio_p.id}/availability/',
            data=json.dumps([{"weekday": 0, "start_time": "09:00", "end_time": "17:00"}]),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {tok.key}',
        )
        self.assertEqual(r.status_code, 403)
        # The owning doctor can
        tok2, _ = Token.objects.get_or_create(user=self.doc_cardio)
        r = self.c.put(
            f'/api/doctors/{self.doc_cardio_p.id}/availability/',
            data=json.dumps([{"weekday": 0, "start_time": "09:00", "end_time": "12:00"}]),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {tok2.key}',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.doc_cardio_p.availabilities.count(), 1)

    def test_slots_endpoint_subtracts_taken(self):
        from rest_framework.authtoken.models import Token
        # Use a fixed upcoming Monday so weekday() == 0 regardless of when tests run
        today = timezone.now().date()
        days_to_monday = (7 - today.weekday()) % 7 or 7
        target = today + timedelta(days=days_to_monday)
        DoctorAvailability.objects.create(
            doctor=self.doc_cardio_p, weekday=0,
            start_time='09:00', end_time='10:30', slot_minutes=30,
        )
        # Book 09:30 so it disappears from slots
        when = timezone.make_aware(
            timezone.datetime.combine(target, timezone.datetime.strptime('09:30', '%H:%M').time())
        ) if timezone.is_aware(timezone.now()) else timezone.datetime.combine(target, timezone.datetime.strptime('09:30', '%H:%M').time())
        Appointment.objects.create(
            patient=self.patient_p, doctor=self.doc_cardio_p,
            scheduled_at=when, reason='taken', status='PENDING',
        )
        tok, _ = Token.objects.get_or_create(user=self.patient)
        r = self.c.get(
            f'/api/doctors/{self.doc_cardio_p.id}/slots/?date={target.isoformat()}',
            HTTP_AUTHORIZATION=f'Token {tok.key}',
        )
        self.assertEqual(r.status_code, 200)
        times = [s['time'] for s in r.json()]
        self.assertIn('09:00', times)
        self.assertNotIn('09:30', times)
        self.assertIn('10:00', times)


# ---------------------------------------------------------------------------
# Layer 3 — Field-level encryption sanity check
# ---------------------------------------------------------------------------

class EncryptionTests(HospitalTestBase):
    """Confirm encrypted fields round-trip correctly through the ORM.

    We're not testing django-encrypted-model-fields itself (it has its own
    test suite), only that our wrapping doesn't break the read-after-write
    contract — which is the part that matters for the §7.3 demonstration.
    """

    def test_encrypted_address_round_trip(self):
        self.patient_p.address = "123 Test Street"
        self.patient_p.save()
        reloaded = Patient.objects.get(pk=self.patient_p.pk)
        self.assertEqual(reloaded.address, "123 Test Street")

    def test_encrypted_phone_round_trip(self):
        self.patient.phone = "+1-555-9999"
        self.patient.save()
        reloaded = User.objects.get(pk=self.patient.pk)
        self.assertEqual(reloaded.phone, "+1-555-9999")


# ---------------------------------------------------------------------------
# Layer 4 — Phase 2.2 REST endpoints (inline role flows)
# ---------------------------------------------------------------------------

class Phase22EndpointTests(HospitalTestBase):
    """One happy path + one wrong-role 403 + one bad-input 400 per new endpoint."""

    def setUp(self):
        super().setUp()
        from rest_framework.authtoken.models import Token
        self.c = Client()
        self.tok_patient = Token.objects.get_or_create(user=self.patient)[0].key
        self.tok_doc = Token.objects.get_or_create(user=self.doc_cardio)[0].key
        self.tok_doc_other = Token.objects.get_or_create(user=self.doc_peds)[0].key
        self.tok_nurse = Token.objects.get_or_create(user=self.nurse_cardio)[0].key
        self.tok_pharma = Token.objects.get_or_create(user=self.pharmacist)[0].key
        self.tok_manager = Token.objects.get_or_create(user=self.manager)[0].key
        self.tok_admin = Token.objects.get_or_create(user=self.admin)[0].key

    def _hdr(self, tok):
        return {'HTTP_AUTHORIZATION': f'Token {tok}'}

    # --- GET /api/me/schedule/ ---
    def test_my_schedule_doctor_sees_own(self):
        r = self.c.get('/api/me/schedule/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 200)
        ids = {row['id'] for row in r.json()}
        self.assertIn(self.appt.id, ids)

    def test_my_schedule_patient_forbidden(self):
        r = self.c.get('/api/me/schedule/', **self._hdr(self.tok_patient))
        self.assertEqual(r.status_code, 403)

    # --- POST /api/appointments/<id>/record/ ---
    def test_add_record_happy(self):
        # Need an appointment WITHOUT a record yet — make a fresh one
        from datetime import timedelta as td
        appt = Appointment.objects.create(
            patient=self.patient_p, doctor=self.doc_cardio_p,
            scheduled_at=timezone.now() + td(days=1),
            reason='Followup', status='CONFIRMED',
        )
        r = self.c.post(
            f'/api/appointments/{appt.id}/record/',
            data={'diagnosis': 'Hypertension', 'notes': 'BP 150/95',
                  'treatment': 'Atenolol'},
            content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 201, r.content)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'COMPLETED')

    def test_add_record_other_doctor_403(self):
        from datetime import timedelta as td
        appt = Appointment.objects.create(
            patient=self.patient_p, doctor=self.doc_cardio_p,
            scheduled_at=timezone.now() + td(days=1, hours=1),
            reason='Followup', status='CONFIRMED',
        )
        r = self.c.post(
            f'/api/appointments/{appt.id}/record/',
            data={'diagnosis': 'X'}, content_type='application/json',
            **self._hdr(self.tok_doc_other),
        )
        self.assertEqual(r.status_code, 403)

    def test_add_record_missing_diagnosis_400(self):
        from datetime import timedelta as td
        appt = Appointment.objects.create(
            patient=self.patient_p, doctor=self.doc_cardio_p,
            scheduled_at=timezone.now() + td(days=1, hours=2),
            reason='Followup', status='CONFIRMED',
        )
        r = self.c.post(
            f'/api/appointments/{appt.id}/record/',
            data={'notes': 'no diagnosis'}, content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 400)

    # --- POST /api/records/<id>/prescribe/ ---
    def test_prescribe_happy(self):
        r = self.c.post(
            f'/api/records/{self.record.id}/prescribe/',
            data={'drug_name': 'Aspirin', 'dosage': '75 mg',
                  'frequency': 'daily', 'duration': '30 days'},
            content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_prescribe_other_doctor_403(self):
        r = self.c.post(
            f'/api/records/{self.record.id}/prescribe/',
            data={'drug_name': 'Aspirin'},
            content_type='application/json',
            **self._hdr(self.tok_doc_other),
        )
        self.assertEqual(r.status_code, 403)

    def test_prescribe_missing_name_400(self):
        r = self.c.post(
            f'/api/records/{self.record.id}/prescribe/',
            data={'dosage': '75 mg'},
            content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 400)

    # --- GET /api/me/department/stock/ ---
    def test_my_dept_stock_doctor(self):
        r = self.c.get('/api/me/department/stock/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 200)
        # Should only contain Cardiology stock
        for row in r.json():
            self.assertEqual(row['department_name'], 'Cardiology')

    def test_my_dept_stock_nurse(self):
        r = self.c.get('/api/me/department/stock/', **self._hdr(self.tok_nurse))
        self.assertEqual(r.status_code, 200)
        for row in r.json():
            self.assertEqual(row['department_name'], 'Cardiology')

    def test_my_dept_stock_patient_403(self):
        r = self.c.get('/api/me/department/stock/', **self._hdr(self.tok_patient))
        self.assertEqual(r.status_code, 403)

    # --- GET /api/me/department/prescriptions/ ---
    def test_my_dept_prescriptions_nurse(self):
        r = self.c.get('/api/me/department/prescriptions/', **self._hdr(self.tok_nurse))
        self.assertEqual(r.status_code, 200)
        rxs = r.json()
        # The seeded Rx is for Cardiology, so the Cardio nurse sees it
        self.assertGreaterEqual(len(rxs), 1)
        for rx in rxs:
            self.assertEqual(rx['department'], 'Cardiology')

    def test_my_dept_prescriptions_doctor_403(self):
        r = self.c.get('/api/me/department/prescriptions/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 403)

    # --- GET /api/me/department/equipment/ ---
    def test_my_dept_equipment_doctor(self):
        r = self.c.get('/api/me/department/equipment/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 200)
        for row in r.json():
            self.assertEqual(row['department_name'], 'Cardiology')

    def test_my_dept_equipment_patient_403(self):
        r = self.c.get('/api/me/department/equipment/', **self._hdr(self.tok_patient))
        self.assertEqual(r.status_code, 403)

    # --- GET /api/drugs/ + POST /api/drugs/ ---
    def test_drugs_list_doctor(self):
        r = self.c.get('/api/drugs/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 200)

    def test_drugs_list_patient_403(self):
        r = self.c.get('/api/drugs/', **self._hdr(self.tok_patient))
        self.assertEqual(r.status_code, 403)

    def test_drugs_create_pharmacist_happy(self):
        r = self.c.post(
            '/api/drugs/',
            data={'name': 'NewDrugZ', 'category': 'OTHER'},
            content_type='application/json',
            **self._hdr(self.tok_pharma),
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_drugs_create_doctor_403(self):
        r = self.c.post(
            '/api/drugs/',
            data={'name': 'Forbidden'}, content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 403)

    def test_drugs_create_missing_name_400(self):
        r = self.c.post(
            '/api/drugs/', data={'category': 'OTHER'},
            content_type='application/json',
            **self._hdr(self.tok_pharma),
        )
        self.assertEqual(r.status_code, 400)

    # --- GET /api/stock/ + PATCH /api/stock/<id>/ ---
    def test_stock_list_pharmacist(self):
        r = self.c.get('/api/stock/', **self._hdr(self.tok_pharma))
        self.assertEqual(r.status_code, 200)
        names = {row['department_name'] for row in r.json()}
        self.assertEqual(names, {'Cardiology', 'Pediatrics'})

    def test_stock_list_doctor_403(self):
        r = self.c.get('/api/stock/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 403)

    def test_stock_adjust_happy(self):
        r = self.c.patch(
            f'/api/stock/{self.cardio_stock.id}/',
            data={'quantity': 99}, content_type='application/json',
            **self._hdr(self.tok_pharma),
        )
        self.assertEqual(r.status_code, 200)
        self.cardio_stock.refresh_from_db()
        self.assertEqual(self.cardio_stock.quantity, 99)

    def test_stock_adjust_doctor_403(self):
        r = self.c.patch(
            f'/api/stock/{self.cardio_stock.id}/',
            data={'quantity': 1}, content_type='application/json',
            **self._hdr(self.tok_doc),
        )
        self.assertEqual(r.status_code, 403)

    def test_stock_adjust_negative_400(self):
        r = self.c.patch(
            f'/api/stock/{self.cardio_stock.id}/',
            data={'quantity': -3}, content_type='application/json',
            **self._hdr(self.tok_pharma),
        )
        self.assertEqual(r.status_code, 400)

    # --- GET /api/management/kpis/ ---
    def test_kpis_manager(self):
        r = self.c.get('/api/management/kpis/', **self._hdr(self.tok_manager))
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn('low_stock', body)
        self.assertIn('equipment_by_status', body)
        self.assertIn('appointments_by_department', body)

    def test_kpis_doctor_403(self):
        r = self.c.get('/api/management/kpis/', **self._hdr(self.tok_doc))
        self.assertEqual(r.status_code, 403)
