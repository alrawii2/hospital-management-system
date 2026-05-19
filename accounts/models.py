"""
Hospital Management System - Domain Models
This file represents the 'Model' layer in MVC.
Every class here corresponds to an entity in your Logical View class diagram.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Field-level encryption (see SAD §7 Security & Privacy).
# These field classes encrypt values with Fernet (AES-128-CBC + HMAC) before
# writing to the DB and decrypt transparently on read. Key is read from the
# FIELD_ENCRYPTION_KEY setting (see hospital_project/settings.py).
from encrypted_model_fields.fields import (
    EncryptedCharField,
    EncryptedTextField,
)


class User(AbstractUser):
    """Base user account. Role determines which profile is attached.

    Six roles, each with a distinct lane in the permission matrix (§3.5):
      PATIENT    - books appointments, sees own data only
      DOCTOR     - clinical write authority for own patients
      NURSE      - clinical read (department-scoped)
      PHARMACIST - drug catalog + stock CRUD (hospital-wide)
      MANAGEMENT - read-only operational oversight (hospital-wide)
      ADMIN      - user/department CRUD via Django admin
    """
    ROLE_CHOICES = [
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
        ('NURSE', 'Nurse'),
        ('PHARMACIST', 'Pharmacist'),
        ('MANAGEMENT', 'Management'),
        ('ADMIN', 'Admin'),
    ]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    # Phone is encrypted at the column level (see SAD §7). Tradeoff:
    # exact-match queries (User.objects.filter(phone=...)) no longer work
    # because Fernet uses a random nonce per write. Phone is rarely queried
    # so the tradeoff is acceptable; email stays plaintext for login lookup.
    phone = EncryptedCharField(max_length=20, blank=True)

    # Make `role` a required prompt during `createsuperuser`
    REQUIRED_FIELDS = ['role']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class Department(models.Model):
    """Hospital department (Cardiology, Pediatrics, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Patient(models.Model):
    """Patient profile - 1:1 with a User of role PATIENT."""
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='patient_profile'
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_type = models.CharField(max_length=5, blank=True)
    # Address is encrypted at the column level (see SAD §7). Address is never
    # queried for, so encryption has zero functional impact here.
    address = EncryptedTextField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Doctor(models.Model):
    """Doctor profile - 1:1 with a User of role DOCTOR."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='doctor_profile'
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='doctors'
    )
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"


class Nurse(models.Model):
    """Nurse profile - 1:1 with a User of role NURSE.

    Nurses are scoped to a Department: they can read prescriptions and
    diagnoses for any patient seen by a doctor in their department, but
    cannot write medical records or prescriptions themselves.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='nurse_profile'
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='nurses'
    )
    license_number = models.CharField(max_length=50, unique=True)
    shift = models.CharField(
        max_length=10,
        choices=[('DAY', 'Day'), ('NIGHT', 'Night'), ('ON_CALL', 'On-Call')],
        default='DAY',
    )

    def __str__(self):
        return f"Nurse {self.user.get_full_name()} ({self.department.name})"


class Pharmacist(models.Model):
    """Pharmacist profile - 1:1 with a User of role PHARMACIST.

    Pharmacists are NOT department-scoped — the hospital pharmacy is a
    central function serving all clinical departments. They have
    hospital-wide read/write authority over Drug catalog and DrugStock.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='pharmacist_profile'
    )
    license_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Pharmacist {self.user.get_full_name()}"


class Manager(models.Model):
    """Manager profile - 1:1 with a User of role MANAGEMENT.

    Operational oversight role: reads aggregate data (stock levels,
    equipment status, department appointment volume) for planning, but
    has NO write authority on clinical or inventory data. User/department
    administration remains with ADMIN.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='manager_profile'
    )
    title = models.CharField(
        max_length=100,
        help_text="e.g. 'Operations Manager', 'Chief of Staff'",
    )

    def __str__(self):
        return f"{self.title}: {self.user.get_full_name()}"


class Appointment(models.Model):
    """An appointment booked by a Patient with a Doctor."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='appointments'
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='appointments'
    )
    scheduled_at = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at']
        # Prevent a doctor from being double-booked at the same instant
        unique_together = ('doctor', 'scheduled_at')

    def __str__(self):
        return f"{self.patient} with {self.doctor} @ {self.scheduled_at:%Y-%m-%d %H:%M}"

    @property
    def is_upcoming(self):
        return self.scheduled_at > timezone.now() and self.status != 'CANCELLED'


class MedicalRecord(models.Model):
    """Notes/diagnosis/treatment created by a Doctor after an Appointment."""
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name='medical_record'
    )
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Record - {self.appointment}"


class Prescription(models.Model):
    """A medication prescribed as part of a MedicalRecord.

    A single MedicalRecord can have many Prescriptions (one per drug).
    Nurses read these (dispensing); Doctors write them.
    """
    medical_record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions'
    )
    drug = models.ForeignKey(
        'Drug', on_delete=models.PROTECT, related_name='prescriptions',
        null=True, blank=True,
        help_text="Optional FK into the Drug catalog. Free-text drug_name "
                  "is still authoritative for legacy records.",
    )
    drug_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g. '500 mg'")
    frequency = models.CharField(max_length=100, help_text="e.g. 'twice daily'")
    duration = models.CharField(max_length=100, help_text="e.g. '7 days'")
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.drug_name} {self.dosage} ({self.frequency})"


# ---------------------------------------------------------------------------
# Inventory: Drug catalog + per-department stock
# ---------------------------------------------------------------------------

class Drug(models.Model):
    """Drug catalog entry.

    A Drug is the *canonical definition* of a medication (name, generic
    name, category, manufacturer, unit). Stock levels are tracked separately
    in DrugStock so the same drug can have different quantities in different
    departments.

    Source for the seeded catalog: WHO Model List of Essential Medicines
    (a public, citable reference list used in §3.2 of the SAD).
    """
    CATEGORY_CHOICES = [
        ('ANALGESIC', 'Analgesic / Pain'),
        ('ANTIBIOTIC', 'Antibiotic'),
        ('ANTIVIRAL', 'Antiviral'),
        ('CARDIO', 'Cardiovascular'),
        ('ENDOCRINE', 'Endocrine / Diabetes'),
        ('GI', 'Gastrointestinal'),
        ('RESP', 'Respiratory'),
        ('PSYCH', 'Psychiatric'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES, default='OTHER')
    manufacturer = models.CharField(max_length=200, blank=True)
    unit = models.CharField(
        max_length=30,
        help_text="Unit of dispense: 'tablet', 'ml', 'vial', etc.",
        default='tablet',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DrugStock(models.Model):
    """Per-department inventory of a Drug.

    There is one DrugStock row per (Drug, Department) pair. Pharmacists
    write; nurses and doctors read (own department only); management reads
    everything.
    """
    drug = models.ForeignKey(
        Drug, on_delete=models.CASCADE, related_name='stock_entries'
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name='drug_stock'
    )
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(
        default=10,
        help_text="Threshold below which the management dashboard flags low stock.",
    )
    expiry_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['department', 'drug']
        unique_together = ('drug', 'department')

    def __str__(self):
        return f"{self.drug.name} @ {self.department.name}: {self.quantity} {self.drug.unit}"

    @property
    def is_low(self):
        return self.quantity <= self.reorder_level


# ---------------------------------------------------------------------------
# Doctor weekly availability — replaces the hardcoded TIME_SLOTS in the SPA.
# ---------------------------------------------------------------------------

class DoctorAvailability(models.Model):
    """One row per weekday block a Doctor is willing to see patients.

    A doctor's full weekly schedule is the union of these rows. The slot grid
    for a given date is generated by walking from start_time to end_time in
    slot_minutes steps, then subtracting slots already taken by Appointments.
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='availabilities'
    )
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveIntegerField(default=30)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['doctor', 'weekday', 'start_time']
        unique_together = ('doctor', 'weekday', 'start_time')

    def __str__(self):
        return f"{self.doctor} {self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class Equipment(models.Model):
    """Medical equipment item assigned to a Department.

    Phase 1: a single record per physical unit (no separate catalog vs
    instance split). Status reflects current operational state. Doctors and
    nurses in the same department can read; management can read all and
    write status. Procurement (creating new units) is admin-side via the
    Django admin.
    """
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('RETIRED', 'Retired'),
    ]

    name = models.CharField(max_length=200)
    model_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='equipment'
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='AVAILABLE'
    )
    last_serviced = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['department', 'name']

    def __str__(self):
        return f"{self.name} ({self.serial_number}) - {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Physical rooms (per Department)
# ---------------------------------------------------------------------------

class Room(models.Model):
    """A physical room within a Department.

    Tracks the operational state (e.g. AVAILABLE, OCCUPIED, MAINTENANCE) so
    management and nursing staff can see where patients can be placed.
    Patients and pharmacists have no business viewing rooms.
    """
    ROOM_TYPE_CHOICES = [
        ('CHECKUP', 'Check-up'),
        ('OPERATING', 'Operating Theater'),
        ('WARD', 'Ward'),
        ('EXAM', 'Examination'),
        ('ICU', 'Intensive Care Unit'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('MAINTENANCE', 'Maintenance'),
        ('CLEANING', 'Cleaning'),
    ]

    number = models.CharField(max_length=20)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='rooms'
    )
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES)
    floor = models.PositiveIntegerField(default=1)
    capacity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='AVAILABLE'
    )

    class Meta:
        ordering = ['department', 'floor', 'number']
        unique_together = ('department', 'number')

    def __str__(self):
        return f"{self.number} ({self.get_room_type_display()}) — {self.department.name}"
