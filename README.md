# Hospital Management System 🏥

A web-based hospital management system covering patient registration, doctor scheduling, appointment booking, medical records, prescriptions, pharmacy inventory, equipment tracking, and operational dashboards.

Built across two iterative phases for the **Software Architecture** course.

- **Phase 1 (delivered 4 May 2026):** architecture design + initial implementation
- **Phase 2 (delivered 21 May 2026):** development & deployment views + production deployment

The architecture follows **Kruchten's 4+1 view model** and is realized in the **Model–View–Controller (MVC) + REST API** style: React 18 SPA frontend communicating with a Django 5 + Django REST Framework backend.

---

## Scope

- **6 roles:** Patient, Doctor, Nurse, Pharmacist, Management, Admin
- **13 domain entities:** User, Patient, Doctor, Nurse, Pharmacist, Manager, Department, Appointment, MedicalRecord, Prescription, Drug, DrugStock, Equipment
- **16 use cases** covering registration, login, booking, prescribing, dispensing, inventory, equipment status, and operational KPIs
- **Centralized RBAC** matrix in `accounts/permissions.py`
- **Field-level encryption** (Fernet AES-128) for `User.phone` and `Patient.address`
- **React SPA** frontend (Vite) connected to a **Django REST Framework** backend
- **Token-based authentication** (`rest_framework.authtoken`)

---

## Quick Start (Phase 1 — local dev)

**Mac / Linux:**
```bash
git clone https://github.com/alrawii2/hospital-management-system.git
cd hospital-management-system
bash setup.sh
```

**Windows:**
git clone https://github.com/alrawii2/hospital-management-system.git
cd hospital-management-system
.\setup.bat

The browser opens automatically at http://localhost:5173

---

## Demo Accounts

| Username | Password | Role |
|---|---|---|
| `patient1` | `test123` | PATIENT |
| `doctor1`–`doctor5` | `test123` | DOCTOR |

For the full set with all roles (password: `Pass1234!`):

```bash
python manage.py seed_data
```

| Tab | Username | Password |
|---|---|---|
| Admin | `admin` | `Pass1234!` |
| Doctor | `doctor_cardio` | `Pass1234!` |
| Nurse | `nurse_cardio` | `Pass1234!` |
| Patient | `patient1` | `Pass1234!` |

---

## Team and Contributions

| Name | Student ID | Role |
|---|---|---|
| Marwan Mohammed Taher Alkhatib | 220911700 | Backend / Domain Engineer |
| Anas Ravioglu | 2309015858 | Frontend / Integration Engineer |
| Saleem Yahya Ahmad Almadfaie | 210911095 | Documentation Engineer |

---

## Course Context

- **Course:** Software Architecture
- **Phase 1 submission:** 4 May 2026
- **Phase 2 submission:** 21 May 2026
- **Repository:** https://github.com/alrawii2/hospital-management-system
