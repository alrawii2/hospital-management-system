from rest_framework import serializers
from django.utils.dateparse import parse_datetime
from datetime import datetime
from .models import (
    User, Doctor, Department, Appointment, Patient, DoctorAvailability,
    MedicalRecord, Prescription, Drug, DrugStock, Equipment,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    department = DepartmentSerializer()

    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization", "years_of_experience", "department"]

    def get_name(self, obj):
        return "Dr. " + obj.user.get_full_name()


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    specialty = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "doctor_name", "specialty", "date", "time", "status", "reason"]

    def get_doctor_name(self, obj):
        return "Dr. " + obj.doctor.user.get_full_name()

    def get_specialty(self, obj):
        return obj.doctor.specialization

    def get_date(self, obj):
        dt = obj.scheduled_at
        if isinstance(dt, str):
            dt = parse_datetime(dt) or datetime.fromisoformat(dt)
        return dt.strftime("%Y-%m-%d")

    def get_time(self, obj):
        dt = obj.scheduled_at
        if isinstance(dt, str):
            dt = parse_datetime(dt) or datetime.fromisoformat(dt)
        return dt.strftime("%H:%M")


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    weekday_label = serializers.SerializerMethodField()

    class Meta:
        model = DoctorAvailability
        fields = [
            "id", "weekday", "weekday_label",
            "start_time", "end_time", "slot_minutes", "active",
        ]

    def get_weekday_label(self, obj):
        return obj.get_weekday_display()


class MedicalRecordSerializer(serializers.ModelSerializer):
    """Diagnosis / notes / treatment for a completed Appointment."""
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)

    class Meta:
        model = MedicalRecord
        fields = ["id", "appointment_id", "diagnosis", "notes", "treatment", "created_at"]


class PrescriptionSerializer(serializers.ModelSerializer):
    """Drug prescribed against a MedicalRecord."""
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    diagnosis = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            "id", "drug", "drug_name", "dosage", "frequency", "duration",
            "instructions", "created_at",
            "doctor_name", "patient_name", "diagnosis", "department",
        ]

    def get_doctor_name(self, obj):
        return "Dr. " + obj.medical_record.appointment.doctor.user.get_full_name()

    def get_patient_name(self, obj):
        u = obj.medical_record.appointment.patient.user
        return u.get_full_name() or u.username

    def get_diagnosis(self, obj):
        return obj.medical_record.diagnosis

    def get_department(self, obj):
        return obj.medical_record.appointment.doctor.department.name


class DrugSerializer(serializers.ModelSerializer):
    """Drug catalog entry."""
    category_display = serializers.SerializerMethodField()

    class Meta:
        model = Drug
        fields = ["id", "name", "generic_name", "category", "category_display",
                  "manufacturer", "unit"]

    def get_category_display(self, obj):
        return obj.get_category_display()


class DrugStockSerializer(serializers.ModelSerializer):
    """One row per (Drug, Department) — quantity and reorder level."""
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    drug_unit = serializers.CharField(source='drug.unit', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    is_low = serializers.BooleanField(read_only=True)

    class Meta:
        model = DrugStock
        fields = ["id", "drug", "drug_name", "drug_unit",
                  "department", "department_name",
                  "quantity", "reorder_level", "expiry_date",
                  "is_low", "last_updated"]


class EquipmentSerializer(serializers.ModelSerializer):
    """Department-assigned medical equipment with operational status."""
    status_display = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Equipment
        fields = ["id", "name", "model_number", "manufacturer", "serial_number",
                  "department", "department_name", "status", "status_display",
                  "last_serviced"]

    def get_status_display(self, obj):
        return obj.get_status_display()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(write_only=True)
    gender = serializers.CharField(write_only=True, max_length=1)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "date_of_birth", "gender"]

    def create(self, validated_data):
        dob = validated_data.pop("date_of_birth")
        gender = validated_data.pop("gender")
        user = User.objects.create_user(**validated_data, role="PATIENT")
        Patient.objects.create(user=user, date_of_birth=dob, gender=gender)
        return user
