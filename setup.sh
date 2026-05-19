#!/bin/bash
# Works on Mac and Linux
# For Windows: use setup.bat instead

echo "======================================"
echo "Hospital Management System - Setup"
echo "======================================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/Frontend/hospital-frontend"

echo ""
echo "Installing backend dependencies..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setting up database..."
cd "$SCRIPT_DIR"
python3 manage.py migrate

echo ""
echo "Creating test users..."
python3 manage.py shell -c "
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
"

echo ""
echo "Starting Django backend..."
cd "$SCRIPT_DIR"
python3 manage.py runserver &
BACKEND_PID=$!

echo ""
echo "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install

echo ""
echo "Starting React frontend..."
npm run dev &
FRONTEND_PID=$!

sleep 3

echo ""
echo "Opening browser..."
# Mac
if command -v open &> /dev/null; then
    open http://localhost:5173
# Linux
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
fi

echo ""
echo "======================================"
echo "Website is ready!"
echo "Go to: http://localhost:5173"
echo "Username: patient1 / Password: test123"
echo "======================================"

wait $BACKEND_PID $FRONTEND_PID
