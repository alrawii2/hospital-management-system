"""
admin.py — registers models with Django admin.
This satisfies the 'Admin manages doctors and departments' use case
without you writing any controllers/templates for it.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Department, Patient, Doctor, Nurse, Pharmacist, Manager,
    Appointment, MedicalRecord, Prescription,
    Drug, DrugStock, Equipment,
    DoctorAvailability, Room,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Info', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Info', {'fields': ('role', 'phone')}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'gender', 'blood_type')
    list_filter = ('gender', 'blood_type')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'specialization', 'license_number', 'years_of_experience')
    list_filter = ('department',)
    search_fields = ('user__first_name', 'user__last_name', 'specialization')


@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'license_number', 'shift')
    list_filter = ('department', 'shift')
    search_fields = ('user__first_name', 'user__last_name', 'license_number')


@admin.register(Pharmacist)
class PharmacistAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number')
    search_fields = ('user__first_name', 'user__last_name', 'license_number')


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ('user', 'title')
    search_fields = ('user__first_name', 'user__last_name', 'title')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_at', 'status')
    list_filter = ('status', 'doctor__department')
    search_fields = ('patient__user__last_name', 'doctor__user__last_name')
    date_hierarchy = 'scheduled_at'


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'created_at')
    search_fields = ('diagnosis', 'notes')


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('drug_name', 'dosage', 'frequency', 'duration', 'medical_record', 'created_at')
    list_filter = ('medical_record__appointment__doctor__department',)
    search_fields = ('drug_name',)


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'category', 'manufacturer', 'unit')
    list_filter = ('category',)
    search_fields = ('name', 'generic_name', 'manufacturer')


@admin.register(DrugStock)
class DrugStockAdmin(admin.ModelAdmin):
    list_display = ('drug', 'department', 'quantity', 'reorder_level', 'expiry_date', 'is_low')
    list_filter = ('department', 'drug__category')
    search_fields = ('drug__name',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'department', 'status', 'last_serviced')
    list_filter = ('department', 'status')
    search_fields = ('name', 'serial_number', 'manufacturer')


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'weekday', 'start_time', 'end_time', 'slot_minutes', 'active')
    list_filter = ('weekday', 'active', 'doctor__department')
    search_fields = ('doctor__user__last_name', 'doctor__user__first_name')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'department', 'room_type', 'floor', 'capacity', 'status')
    list_filter = ('department', 'room_type', 'status', 'floor')
    search_fields = ('number',)
