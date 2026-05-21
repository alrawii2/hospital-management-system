Hospital Management System 🏥

A web-based hospital management system covering patient registration, doctor
scheduling, appointment booking, medical records, prescriptions, pharmacy
inventory, equipment tracking, and operational dashboards.
Built across two iterative phases for the Software Architecture course.

Phase 1 (delivered 4 May 2026): architecture design + initial implementation
Phase 2 (delivered 21 May 2026): development & deployment views + production deployment

The architecture follows Kruchten's 4+1 view model and is realized in the
Model–View–Controller (MVC) + REST API style: React 18 SPA frontend
communicating with a Django 5 + Django REST Framework backend.

Scope

6 roles: Patient, Doctor, Nurse, Pharmacist, Management, Admin
13 domain entities: User, Patient, Doctor, Nurse, Pharmacist, Manager,
Department, Appointment, MedicalRecord, Prescription, Drug, DrugStock,
Equipment
16 use cases covering registration, login, booking, prescribing,
dispensing, inventory, equipment status, and operational KPIs
Centralized RBAC matrix in accounts/permissions.py
Field-level encryption (Fernet AES-128) for User.phone and Patient.address
React SPA frontend (Vite) connected to a Django REST Framework backend
Token-based authentication (rest_framework.authtoken)
Docker-based production deployment (Nginx + Gunicorn + PostgreSQL + Redis)


Quick start (Phase 1 — local dev, no Docker)
Mac / Linux:
bashgit clone https://github.com/alrawii2/hospital-management-system.git
cd hospital-management-system
bash setup.sh
Windows:
batgit clone https://github.com/alrawii2/hospital-management-system.git
cd hospital-management-system
.\setup.bat
The browser opens automatically at http://localhost:5173.
Quick start (Phase 2 — full Docker stack)
bashgit clone https://github.com/alrawii2/hospital-management-system.git
cd hospital-management-system
cp deployment/.env.example .env       # then edit secrets
docker compose -f deployment/docker-compose.yml up --build
Visit http://localhost (port 80). Nginx serves the React build and
reverse-proxies /api/* and /admin/ to Django.

Demo accounts
A quick set is created by setup.sh:
UsernamePasswordRolepatient1test123PATIENTdoctor1..5test123DOCTOR
For the richer set with one user per role (admin, pharmacist, manager,
nurse, multiple doctors, multiple patients) — all with password Pass1234!:
bashpython manage.py seed_data
That gives you credentials for every tab on the role-tabbed login screen
(Admin / Doctor / Nurse / Patient):
TabUsernamePasswordAdminadminPass1234!Doctordoctor_cardioPass1234!Nursenurse_cardioPass1234!Patientpatient1Pass1234!
