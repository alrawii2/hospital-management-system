from accounts.models import User, Patient, Doctor, Department
from datetime import date

if not User.objects.filter(username='patient1').exists():
    u = User.objects.create_user(username='patient1', password='test123', first_name='Alex', last_name='Johnson', role='PATIENT')
    Patient.objects.create(user=u, date_of_birth=date(1995,1,1), gender='M')
    print('Patient created!')
else:
    print('Patient already exists!')

if not Department.objects.filter(name='Cardiology').exists():
    d1 = Department.objects.create(name='Cardiology')
    d2 = Department.objects.create(name='Neurology')
    d3 = Department.objects.create(name='Pediatrics')
    d4 = Department.objects.create(name='Orthopedics')
    d5 = Department.objects.create(name='Dermatology')
    u2 = User.objects.create_user(username='doctor1', password='test123', first_name='Ayse', last_name='Kaya', role='DOCTOR')
    Doctor.objects.create(user=u2, department=d1, specialization='Cardiology', license_number='LIC001', years_of_experience=10)
    u3 = User.objects.create_user(username='doctor2', password='test123', first_name='Mehmet', last_name='Celik', role='DOCTOR')
    Doctor.objects.create(user=u3, department=d2, specialization='Neurology', license_number='LIC002', years_of_experience=8)
    u4 = User.objects.create_user(username='doctor3', password='test123', first_name='Sara', last_name='Yildiz', role='DOCTOR')
    Doctor.objects.create(user=u4, department=d3, specialization='Pediatrics', license_number='LIC003', years_of_experience=6)
    u5 = User.objects.create_user(username='doctor4', password='test123', first_name='Emre', last_name='Demir', role='DOCTOR')
    Doctor.objects.create(user=u5, department=d4, specialization='Orthopedics', license_number='LIC004', years_of_experience=12)
    u6 = User.objects.create_user(username='doctor5', password='test123', first_name='Leyla', last_name='Arslan', role='DOCTOR')
    Doctor.objects.create(user=u6, department=d5, specialization='Dermatology', license_number='LIC005', years_of_experience=5)
    print('Doctors created!')
else:
    print('Doctors already exist!')

print('Setup complete!')
