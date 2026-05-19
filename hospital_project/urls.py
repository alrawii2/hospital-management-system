from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from accounts import views as account_views
from accounts import api_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/register/', account_views.register_patient, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', account_views.dashboard, name='dashboard'),
    path('appointments/doctors/', account_views.doctor_list, name='doctor_list'),
    path('appointments/book/<int:doctor_id>/', account_views.book_appointment, name='book_appointment'),
    path('appointments/my/', account_views.my_appointments, name='my_appointments'),
    path('appointments/schedule/', account_views.doctor_schedule, name='doctor_schedule'),
    path('appointments/<int:appointment_id>/record/', account_views.add_medical_record, name='add_medical_record'),
    path('records/<int:record_id>/prescribe/', account_views.add_prescription, name='add_prescription'),
    path('nurse/prescriptions/', account_views.nurse_prescriptions, name='nurse_prescriptions'),
    path('pharmacy/drugs/', account_views.drug_catalog, name='drug_catalog'),
    path('pharmacy/drugs/new/', account_views.drug_create, name='drug_create'),
    path('pharmacy/stock/', account_views.drug_stock_list, name='drug_stock_list'),
    path('pharmacy/stock/<int:stock_id>/adjust/', account_views.drug_stock_adjust, name='drug_stock_adjust'),
    path('equipment/', account_views.equipment_list, name='equipment_list'),
    path('equipment/<int:equipment_id>/edit/', account_views.equipment_edit, name='equipment_edit'),
    path('management/', account_views.management_dashboard, name='management_dashboard'),
    path('api/health/', api_views.api_health, name='api_health'),
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/register/', api_views.api_register, name='api_register'),
    path('api/logout/', api_views.api_logout, name='api_logout'),
    path('api/doctors/', api_views.api_doctor_list, name='api_doctor_list'),
    path('api/appointments/', api_views.api_my_appointments, name='api_my_appointments'),
    path('api/appointments/book/<int:doctor_id>/', api_views.api_book_appointment, name='api_book_appointment'),
    path('api/appointments/<int:appointment_id>/cancel/', api_views.api_cancel_appointment, name='api_cancel_appointment'),
    path('api/doctors/<int:doctor_id>/availability/', api_views.api_doctor_availability, name='api_doctor_availability'),
    path('api/doctors/<int:doctor_id>/slots/', api_views.api_doctor_slots, name='api_doctor_slots'),
    # Phase 2.2 — inline role flows
    path('api/me/schedule/', api_views.api_my_schedule, name='api_my_schedule'),
    path('api/appointments/<int:appointment_id>/record/', api_views.api_add_medical_record, name='api_add_medical_record'),
    path('api/records/<int:record_id>/prescribe/', api_views.api_add_prescription, name='api_add_prescription'),
    path('api/me/department/stock/', api_views.api_my_department_stock, name='api_my_department_stock'),
    path('api/me/department/prescriptions/', api_views.api_my_department_prescriptions, name='api_my_department_prescriptions'),
    path('api/me/department/equipment/', api_views.api_my_department_equipment, name='api_my_department_equipment'),
    path('api/drugs/', api_views.api_drugs, name='api_drugs'),
    path('api/stock/', api_views.api_stock_list, name='api_stock_list'),
    path('api/stock/<int:stock_id>/', api_views.api_stock_adjust, name='api_stock_adjust'),
    path('api/management/kpis/', api_views.api_management_kpis, name='api_management_kpis'),
]
