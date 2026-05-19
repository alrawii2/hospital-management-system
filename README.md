# Hospital Management System 🏥

A web-based hospital management system covering patient registration, doctor
scheduling, appointment booking, medical records, prescriptions, pharmacy
inventory, equipment tracking, and operational dashboards.

Built across two iterative phases for the **Software Architecture** course.

- **Phase 1 (delivered 4 May 2026):** architecture design + initial implementation
- **Phase 2 (delivered 24 May 2026):** development & deployment views + production deployment
- **Phase 2.1 (delivered 17 May 2026):** patient cancellation, doctor availability,
  Room model, expanded dataset

The architecture follows **Kruchten's 4+1 view model** and is realized in the
**Model–View–Controller (MVC) + REST API** style: React 18 SPA frontend
communicating with a Django 5 + Django REST Framework backend.

---

## Scope

- **6 roles:** Patient, Doctor, Nurse, Pharmacist, Management, Admin
- **15 domain entities:** User, Patient, Doctor, Nurse, Pharmacist, Manager,
  Department, Appointment, MedicalRecord, Prescription, Drug, DrugStock,
  Equipment, DoctorAvailability, Room
- **18 use cases** covering registration, login, booking, cancellation,
  doctor availability, prescribing, dispensing, inventory, equipment
  status, and operational KPIs
- **Centralized RBAC** matrix in `accounts/permissions.py`
- **Field-level encryption** (Fernet AES-128) for `User.phone` and `Patient.address`
- **React SPA** frontend (Vite) connected to a **Django REST Framework** backend
- **Token-based authentication** (`rest_framework.authtoken`)
- **Docker-based production deployment** (Nginx + Gunicorn + PostgreSQL + Redis)

---

## Requirements

Install these before running any of the quick-start blocks below.

| Tool          | Version          | Notes                                              |
|---------------|------------------|----------------------------------------------------|
| Python        | **3.12.x**       | Pinned via `.python-version`. 3.11 also works.    |
| pip           | bundled with Python | `python -m pip --version` to confirm            |
| Node.js       | **≥ 20.19 LTS**  | Pinned via `Frontend/hospital-frontend/.nvmrc`     |
| npm           | ≥ 10             | Ships with Node 20.                                |
| Git           | any recent       | 2.40+ recommended for `.gitattributes` support     |
| Docker Engine | 24+ (Phase 2)    | Only needed for the full Docker stack              |
| Docker Compose | v2 (Phase 2)    | `docker compose` (not `docker-compose`)            |

Optional but useful: a virtual-environment manager (`venv`, `pyenv`, `conda`)
and Node version manager (`nvm`, `fnm`, `volta`).

---

## Quick start (Phase 1 — local dev, no Docker)

The `setup` scripts install backend + frontend deps, run migrations,
seed a minimal demo user set, and launch both servers.

### macOS / Linux

```bash
git clone https://github.com/mars741/hospital-management-system-.git
cd hospital-management-system-
chmod +x setup.sh
bash setup.sh
```

### Windows (Command Prompt or PowerShell)

```bat
git clone https://github.com/mars741/hospital-management-system-.git
cd hospital-management-system-
.\setup.bat
```

The browser opens automatically at <http://localhost:5173>.

> **Manual run** — if you'd rather start each piece yourself, see
> [How to run manually](#how-to-run-manually) below.

## Quick start (Phase 2 — full Docker stack)

### macOS / Linux

```bash
git clone https://github.com/mars741/hospital-management-system-.git
cd hospital-management-system-
cp deployment/.env.example .env       # then edit secrets
docker compose -f deployment/docker-compose.yml up --build
```

### Windows (Command Prompt)

```bat
git clone https://github.com/mars741/hospital-management-system-.git
cd hospital-management-system-
copy deployment\.env.example .env
docker compose -f deployment\docker-compose.yml up --build
```

### Windows (PowerShell)

```powershell
git clone https://github.com/mars741/hospital-management-system-.git
cd hospital-management-system-
Copy-Item deployment\.env.example .env
docker compose -f deployment\docker-compose.yml up --build
```

Visit <http://localhost> (port 80). Nginx serves the React build and
reverse-proxies `/api/*` and `/admin/` to Django.

---

## How to run manually

Skip the `setup` script if you want full control (e.g. you already
have a virtualenv, or just one of the two servers).

### Backend — Django

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data           # rich demo set (Pass1234!)
python manage.py runserver 8000
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver 8000
```

**Windows (Command Prompt):**
```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver 8000
```

> If PowerShell blocks `Activate.ps1` with an execution-policy error, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Frontend — React + Vite

In a second terminal, from the repo root:

**macOS / Linux:**
```bash
cd Frontend/hospital-frontend
npm install
npm run dev
```

**Windows (PowerShell or Command Prompt):**
```bat
cd Frontend\hospital-frontend
npm install
npm run dev
```

Then open <http://localhost:5173>. The backend must be running at
`http://localhost:8000` for the frontend to authenticate.

### Running the tests

```bash
python manage.py test accounts
```

(Same command on every OS; no extra setup.)

---

## Demo accounts

A quick set is created by `setup.sh`:

| Username    | Password | Role       |
|-------------|----------|------------|
| `patient1`  | `test123`| PATIENT    |
| `doctor1..5`| `test123`| DOCTOR     |

For the richer set with one user per role (admin, pharmacist, manager,
nurse, multiple doctors, multiple patients) — all with password `Pass1234!`:

```bash
python manage.py seed_data
```

That gives you credentials for every tab on the role-tabbed login screen
(Admin / Doctor / Nurse / Patient):

| Tab     | Username           | Password    |
|---------|--------------------|-------------|
| Admin   | `admin`            | `Pass1234!` |
| Doctor  | `doctor_cardio`    | `Pass1234!` |
| Nurse   | `nurse_cardio`     | `Pass1234!` |
| Patient | `patient1`         | `Pass1234!` |

---

## Architecture at a glance

**MVC + REST API layers:**

| Layer            | Where it lives                                        |
|------------------|-------------------------------------------------------|
| View (Frontend)  | React SPA — `Frontend/hospital-frontend/src/App.jsx`  |
| API Bridge       | DRF — `accounts/api_views.py`, `accounts/serializers.py`|
| Controller       | `accounts/views.py` — request handlers per use case   |
| Model            | `accounts/models.py` — 15 ORM entities                |

**Cross-cutting:**

- `accounts/permissions.py` — RBAC matrix (single source of truth)
- `accounts/forms.py` — input validation
- `accounts/admin.py` — Django admin config
- `hospital_project/urls.py` — URL routing
- `hospital_project/settings.py` — env-driven configuration

**4+1 views — coverage per phase:**

| View         | Section in SAD v2 | Phase 1 | Phase 2  |
|--------------|-------------------|---------|----------|
| Use Case     | §2                | ✅      | ✅       |
| Logical      | §3                | ✅      | ✅       |
| Process      | §4                | ✅      | ✅       |
| Development  | §7 (new)          | —       | ✅       |
| Deployment   | §8 (expanded)     | stub    | ✅       |

---

## Repository layout

```
.
├── README.md
├── SAD.docx                              ← Phase 1 SAD (v1.0)
├── SAD_v2.docx                           ← Phase 2 SAD (v2.0, extended)
├── setup.sh / setup.bat                  ← Local dev setup (no Docker)
├── seed.py                               ← Minimal seed (legacy)
├── requirements.txt                      ← Python deps incl. Phase 2 prod
├── manage.py
├── hospital_project/                     ← Django project settings + URLs
├── accounts/                             ← Models, views, API, permissions
│   ├── models.py                         ← 15 domain entities
│   ├── api_views.py                      ← REST API endpoints
│   ├── serializers.py                    ← JSON serializers
│   ├── permissions.py                    ← Centralized RBAC matrix
│   ├── views.py                          ← Template-based controllers
│   ├── forms.py                          ← Input validation
│   ├── admin.py                          ← Django admin config
│   └── management/commands/seed_data.py  ← Rich demo data
├── Frontend/hospital-frontend/           ← React SPA
│   └── src/
│       ├── App.jsx                       ← Login, Sidebar, Dashboard, Book, View,
│       │                                   MyAvailability, ConfirmCancelDialog (Phase 2.1)
│       └── App.css                       ← Custom design system
├── deployment/                           ← Phase 2 deployment infrastructure
│   ├── Dockerfile.backend                ← Django + Gunicorn image
│   ├── Dockerfile.frontend               ← React build + Nginx image
│   ├── docker-compose.yml                ← Full stack (db + redis + backend + nginx)
│   ├── nginx.conf                        ← Nginx site config (static + reverse proxy)
│   ├── entrypoint.sh                     ← Backend entrypoint (migrate, collectstatic, gunicorn)
│   ├── .env.example                      ← Environment template
│   └── .dockerignore
├── *.puml                                ← PlantUML sources at the project root
│   ├── use_case_diagram.puml             ← Use Case View
│   ├── class_diagram.puml                ← Logical View
│   ├── sequence_diagram.puml             ← Process View — Phase 1 (legacy)
│   ├── sequence_diagram_v2.puml          ← Process View — Phase 2 (React + REST)
│   ├── activity_diagram.puml             ← Process View — appointment lifecycle
│   ├── sequence_prescription_workflow.puml  ← Process View — prescription workflow
│   ├── component_diagram.puml            ← Development View (new in Phase 2)
│   └── deployment_diagram.puml           ← Deployment View (new in Phase 2)
└── .github/workflows/ci.yml              ← CI: backend tests, frontend build, image smoke
```

---

## Tech stack

- Python 3.12 + Django 5.2 + Django REST Framework 3.15
- React 18 + Vite 5
- PostgreSQL 15 (prod) · SQLite 3 (dev fallback)
- Redis 7 (cache + DRF throttling)
- Nginx 1.25 (reverse proxy + static)
- Gunicorn 21 (WSGI app server)
- Docker + Docker Compose for deployment
- Token-based authentication (`rest_framework.authtoken`)
- Field-level encryption via `django-encrypted-model-fields` (Fernet AES-128)

---

## Team and Contributions

| Name                                | Student ID  | Role                            |
|-------------------------------------|-------------|---------------------------------|
| Marwan Mohammed Taher Alkhatib      | 220911700   | Backend / Domain Engineer       |
| Anas Ravioglu                       | 2309015858  | Frontend / Integration Engineer |
| Saleem Yahya Ahmad Almadfaie        | 210911095   | Documentation Engineer          |

Per-phase contributions are documented in the SAD (§"Team and Contributions").

---

## Course context

- **Course:** Software Architecture
- **Phase 1 submission:** 4 May 2026
- **Phase 2 submission:** 24 May 2026
