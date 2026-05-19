"""
forms.py — Form classes used by Controllers (views).
Forms validate input before it reaches the Model layer.

This file mixes accounts and appointments forms for simplicity.
In a stricter app split, put PatientRegistrationForm in accounts/forms.py
and AppointmentForm/MedicalRecordForm in appointments/forms.py.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import (
    User, Patient, Appointment, MedicalRecord, Prescription,
    Drug, DrugStock, Equipment,
)


class PatientRegistrationForm(UserCreationForm):
    """Registers a new User (role=PATIENT) AND creates the Patient profile."""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(choices=Patient.GENDER_CHOICES)
    blood_type = forms.CharField(max_length=5, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',
                  'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'PATIENT'
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
            Patient.objects.create(
                user=user,
                date_of_birth=self.cleaned_data['date_of_birth'],
                gender=self.cleaned_data['gender'],
                blood_type=self.cleaned_data.get('blood_type', ''),
                address=self.cleaned_data.get('address', ''),
            )
        return user


class AppointmentForm(forms.ModelForm):
    """Patient books an appointment with a chosen doctor."""

    class Meta:
        model = Appointment
        fields = ('scheduled_at', 'reason')
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_scheduled_at(self):
        scheduled = self.cleaned_data['scheduled_at']
        if scheduled <= timezone.now():
            raise forms.ValidationError("Appointment time must be in the future.")
        return scheduled


class MedicalRecordForm(forms.ModelForm):
    """Doctor records diagnosis/treatment after an appointment."""

    class Meta:
        model = MedicalRecord
        fields = ('diagnosis', 'notes', 'treatment')
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'treatment': forms.Textarea(attrs={'rows': 3}),
        }


class PrescriptionForm(forms.ModelForm):
    """Doctor prescribes a medication tied to a MedicalRecord.

    Nurses do NOT use this form — they have read-only access to prescriptions
    via the nurse dashboard. Write access is enforced in views.py via
    permissions.can_write_prescription().

    `drug` is an optional FK into the Drug catalog. If selected, drug_name
    is auto-populated from the catalog entry on save.
    """

    class Meta:
        model = Prescription
        fields = ('drug', 'drug_name', 'dosage', 'frequency', 'duration', 'instructions')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        drug = cleaned.get('drug')
        drug_name = cleaned.get('drug_name')
        if drug and not drug_name:
            cleaned['drug_name'] = drug.name
        if not drug and not drug_name:
            raise forms.ValidationError(
                "Pick a drug from the catalog or enter a drug name manually."
            )
        return cleaned


# ---------------------------------------------------------------------------
# Inventory forms (Pharmacist + Management)
# ---------------------------------------------------------------------------

class DrugForm(forms.ModelForm):
    """Pharmacist creates/edits an entry in the Drug catalog."""

    class Meta:
        model = Drug
        fields = ('name', 'generic_name', 'category', 'manufacturer', 'unit')


class DrugStockForm(forms.ModelForm):
    """Pharmacist adjusts a (Drug, Department) stock row."""

    class Meta:
        model = DrugStock
        fields = ('drug', 'department', 'quantity', 'reorder_level', 'expiry_date')
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }


class EquipmentForm(forms.ModelForm):
    """Management updates an Equipment row (typically just `status`)."""

    class Meta:
        model = Equipment
        fields = ('name', 'model_number', 'manufacturer', 'serial_number',
                  'department', 'status', 'last_serviced')
        widgets = {
            'last_serviced': forms.DateInput(attrs={'type': 'date'}),
        }
