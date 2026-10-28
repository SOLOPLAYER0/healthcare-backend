# Shashank Pratyush
# Healthcare Backend (Django + DRF + PostgreSQL + JWT)

A REST API where users register, log in with email and password, manage their own
patients, manage doctors, and assign doctors to patients.

**Stack:** Python 3.10+, Django 5.2, Django REST Framework, `djangorestframework-simplejwt`,
PostgreSQL (via `psycopg` 3), `python-dotenv`.

---

## Table of contents
1. [Project structure](#1-project-structure)
2. [Prerequisites](#2-prerequisites)
3. [Virtual environment and dependencies](#3-virtual-environment-and-dependencies)
4. [PostgreSQL setup](#4-postgresql-setup)
5. [Environment variables](#5-environment-variables)
6. [Migrations, superuser, run server](#6-migrations-superuser-run-server)
7. [API reference](#7-api-reference)
8. [Postman testing guide](#8-postman-testing-guide)
9. [Automated tests](#9-automated-tests)
10. [Design decisions and extra fields](#10-design-decisions-and-extra-fields)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Project structure

```
healthcare_backend/
├── manage.py
├── requirements.txt
├── .env.example            # placeholder values only (copy to .env)
├── .gitignore
├── config/                 # project package
│   ├── settings.py         # env-driven settings, PostgreSQL, DRF, JWT
│   ├── urls.py
│   ├── exceptions.py       # consistent JSON errors, no internals leaked
│   └── testing.py          # shared test helpers
├── users/                  # custom email-based User, register/login
├── patients/               # Patient model + CRUD (owner-scoped)
├── doctors/                # Doctor model + CRUD (creator-only modification)
├── mappings/               # PatientDoctorMapping + endpoints
└── postman/healthcare_backend.postman_collection.json
```

## 2. Prerequisites

- Python 3.10 or newer (`python --version`)
- PostgreSQL 13 or newer (server and `psql`)
- Postman (for manual API testing)
- Git (optional)

## 3. Virtual environment and dependencies

**Windows (PowerShell):**
```powershell
cd healthcare_backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
(Command Prompt: `venv\Scripts\activate.bat`.)

**Linux / macOS:**
```bash
cd healthcare_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Packages (see `requirements.txt`): `Django`, `djangorestframework`,
`djangorestframework-simplejwt`, `psycopg[binary]`, `python-dotenv`.
`psycopg[binary]` ships its own PostgreSQL client library, so no compiler is needed.

## 4. PostgreSQL setup

Install PostgreSQL: https://www.postgresql.org/download/ (Windows installer, or
`sudo apt install postgresql` on Debian/Ubuntu). Then create the database and user.

**Linux:** `sudo -u postgres psql`  
**Windows:** open "SQL Shell (psql)" and log in as `postgres` with the password chosen during install.

```sql
CREATE USER healthcare_user WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE healthcare_db OWNER healthcare_user;
ALTER USER healthcare_user CREATEDB;   -- needed so `manage.py test` can create a test database
\q
```

Check the connection:
```bash
psql -h localhost -U healthcare_user -d healthcare_db
```

## 5. Environment variables

Copy the example file and fill in real values:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

| Variable | Meaning |
|---|---|
| `DJANGO_SECRET_KEY` | Long random string. Generate: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DJANGO_DEBUG` | `True` for local development, `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts, e.g. `localhost,127.0.0.1` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | The database/user created above |
| `DB_HOST`, `DB_PORT` | Usually `localhost` and `5432` |

`.env` is listed in `.gitignore`; never commit it. The app refuses to start with a clear
message if a required variable is missing.

## 6. Migrations, superuser, run server

Migration files are included in the repository. Apply them:

```bash
python manage.py migrate
```

(If you change a model: `python manage.py makemigrations` then `migrate`.)

Optional, for the Django admin at `/admin/` (login with email + password):
```bash
python manage.py createsuperuser
```

Start the server:
```bash
python manage.py runserver
```
The API is now at `http://127.0.0.1:8000/`.

## 7. API reference

All endpoints except register/login require the header
`Authorization: Bearer <access_token>`.

Error responses always look like:
```json
{ "success": false, "message": "Validation failed.", "errors": { "email": ["..."] } }
```
(`errors` appears for validation failures only.)

### Authentication

| Method | URL | Description | Success |
|---|---|---|---|
| POST | `/api/auth/register/` | Create account | 201 |
| POST | `/api/auth/login/` | Get JWT access and refresh tokens | 200 |
| POST | `/api/auth/token/refresh/` | *(extra)* New access token from refresh token | 200 |

**Register**: request
```json
{ "name": "Alice", "email": "alice@example.com", "password": "StrongPass#2026" }
```
response `201`
```json
{ "success": true, "message": "User registered successfully.",
  "user": { "id": 1, "name": "Alice", "email": "alice@example.com" } }
```
Errors: `400` for missing/invalid fields, duplicate email (case-insensitive), or a weak
password (min 8 chars, not common, not all numeric, not similar to name/email).

**Login**: request
```json
{ "email": "alice@example.com", "password": "StrongPass#2026" }
```
response `200`
```json
{ "success": true, "message": "Login successful.",
  "access": "<jwt>", "refresh": "<jwt>",
  "user": { "id": 1, "name": "Alice", "email": "alice@example.com" } }
```
Wrong email or password: `401` `{"success": false, "message": "Invalid email or password."}`
(the same message for unknown email and wrong password). Access tokens last 30 minutes,
refresh tokens 1 day.

### Patients (private to the creating user)

| Method | URL | Description | Success |
|---|---|---|---|
| POST | `/api/patients/` | Create patient | 201 |
| GET | `/api/patients/` | List **your** patients | 200 |
| GET | `/api/patients/<id>/` | Get one | 200 |
| PUT | `/api/patients/<id>/` | Update (all required fields) | 200 |
| DELETE | `/api/patients/<id>/` | Delete | 204 |

Create request:
```json
{ "name": "John Doe", "date_of_birth": "1990-05-15", "gender": "male",
  "contact_number": "+91 98765 43210", "address": "12 Park Street, Delhi",
  "medical_history": "Mild asthma" }
```
Response `201`:
```json
{ "id": 1, "name": "John Doe", "date_of_birth": "1990-05-15", "age": 36,
  "gender": "male", "contact_number": "+91 98765 43210",
  "address": "12 Park Street, Delhi", "medical_history": "Mild asthma",
  "created_at": "2026-10-28T01:43:31.362249Z", "updated_at": "2026-10-28T01:43:31.362258Z" }
```
`gender` is one of `male`, `female`, `other`. `age` is computed. `owner` is never accepted
from the request; it is always the authenticated user. Another user's patient ID returns
`404`, exactly like a nonexistent one, so IDs cannot be probed. (`PATCH` also works.)

### Doctors (visible to all users; modifiable only by the creator)

| Method | URL | Description | Success |
|---|---|---|---|
| POST | `/api/doctors/` | Create doctor | 201 |
| GET | `/api/doctors/` | List all doctors | 200 |
| GET | `/api/doctors/<id>/` | Get one | 200 |
| PUT | `/api/doctors/<id>/` | Update (creator only, else `403`) | 200 |
| DELETE | `/api/doctors/<id>/` | Delete (creator only, else `403`) | 204 |

Create request:
```json
{ "name": "Meera Sharma", "specialization": "Cardiology",
  "email": "meera.sharma@example.com", "contact_number": "+91 91234 56789",
  "years_of_experience": 12 }
```
Doctor `email` must be unique (`400` otherwise).

### Patient-doctor mappings

| Method | URL | Description | Success |
|---|---|---|---|
| POST | `/api/mappings/` | Assign a doctor to one of your patients | 201 |
| GET | `/api/mappings/` | All mappings for your patients | 200 |
| GET | `/api/mappings/<patient_id>/` | All doctors assigned to that patient | 200 |
| DELETE | `/api/mappings/<id>/` | Remove an assignment (`<id>` is the **mapping** id) | 204 |

> Note: as specified by the assignment, `<id>` means a **patient id** for `GET` and a
> **mapping id** for `DELETE`.
>
> Note on `GET /api/mappings/`: it returns *all* mappings the authenticated user is
> allowed to see, i.e. every mapping for patients that user owns. Mappings of other users'
> patients are deliberately excluded, because patient records are private to their creator.
> To make it list literally every mapping in the system, change `get_queryset()` in
> `mappings/views.py` to `PatientDoctorMapping.objects.select_related("patient", "doctor")`.

Create request `{ "patient": 1, "doctor": 1 }`, response `201`:
```json
{ "id": 1,
  "patient": { "id": 1, "name": "John Doe", "gender": "male", "date_of_birth": "1990-05-15", "contact_number": "+91 98765 43210" },
  "doctor":  { "id": 1, "name": "Meera Sharma", "specialization": "Cardiology", "email": "meera.sharma@example.com", "contact_number": "+91 91234 56789" },
  "assigned_at": "2026-10-28T01:43:31.402000Z" }
```
Errors: `400` for a nonexistent doctor or patient (`"Doctor not found."`/`"Patient not found."`),
a patient you do not own (same message as nonexistent), or a duplicate assignment
(`"This doctor is already assigned to this patient."`, also enforced by a database unique
constraint). `404` for an unknown/foreign patient on `GET /api/mappings/<patient_id>/` or
mapping on `DELETE`.

### Status code summary

| Code | When |
|---|---|
| 200 / 201 / 204 | Success / created / deleted |
| 400 | Validation failure, duplicates, invalid IDs in a request body |
| 401 | Missing, invalid, or expired token; wrong login credentials |
| 403 | Authenticated but not allowed (modifying someone else's doctor) |
| 404 | Resource does not exist (or is not yours, for patients and mappings) |
| 405 | Method not supported on that URL |
| 500 | Unexpected server/database error (generic message; details only in server log) |

## 8. Postman testing guide

### Option A: import the ready-made collection
1. Postman, **Import**, choose `postman/healthcare_backend.postman_collection.json`.
2. Make sure the server is running. The `base_url` variable defaults to `http://127.0.0.1:8000`.
3. Run requests in order, folder 1 to 5 (or use the Collection Runner). Test scripts store
   `access_token`, `refresh_token`, `patient_id`, `doctor_id` and `mapping_id` automatically
   and assert the expected status code of every request.

### Option B: by hand
Use header `Content-Type: application/json` and, after login,
`Authorization: Bearer <access>` (or Postman's *Authorization* tab, type *Bearer Token*).

Correct order:
1. `POST /api/auth/register/`: body shown above, expect **201**.
2. `POST /api/auth/login/`: copy the `access` token, expect **200**.
3. `POST /api/patients/`: note the returned `id`, expect **201**.
4. `GET /api/patients/` and `GET /api/patients/<id>/`: expect **200**.
5. `PUT /api/patients/<id>/`: full body with changed values, expect **200**.
6. `POST /api/doctors/`: note the returned `id`, expect **201**.
7. `GET /api/doctors/`, `GET /api/doctors/<id>/`, `PUT /api/doctors/<id>/`: expect **200**.
8. `POST /api/mappings/` with `{"patient": <pid>, "doctor": <did>}`: expect **201**; repeat it and expect **400**.
9. `GET /api/mappings/` and `GET /api/mappings/<patient_id>/`: expect **200**.
10. `DELETE /api/mappings/<mapping_id>/`: expect **204**.
11. `DELETE /api/doctors/<id>/` and `DELETE /api/patients/<id>/`: expect **204**; a following `GET` gives **404**.

Negative checks worth trying: no token (401), a garbage token (401), another user's
patient ID (404), editing a doctor you did not create (403, register a second user to try).

## 9. Automated tests

106 tests (DRF `APITestCase`) cover registration, login, JWT enforcement, patient/doctor CRUD,
ownership restrictions, mappings, duplicate prevention, invalid IDs, validation errors and
unauthenticated access. They run against PostgreSQL in a separate throwaway database
(`test_<DB_NAME>`) that Django creates and drops, so your data is untouched.

```bash
python manage.py test                 # everything
python manage.py test patients        # one app
python manage.py test -v 2            # verbose
```
The database user needs the `CREATEDB` privilege (see section 4). The suite takes about a
minute because password hashing is deliberately slow.

## 10. Design decisions and extra fields

- **Custom `User` model** (`users.User`) with `email` as the login identifier plus `name`;
  an `EmailBackend` makes email login work for the API and the admin. Passwords are hashed
  by `create_user()` (PBKDF2) and never returned.
- **Patient** extra fields beyond the basics: `medical_history` (optional text), `age`
  (computed, read-only), timestamps.
- **Doctor** extra fields: `email` (unique), `years_of_experience`, `created_by`, timestamps.
  `created_by` enforces "only the creator may modify or delete"; if the creator's account is
  deleted the doctor remains visible but read-only.
- **Mapping** is its own table with a `UniqueConstraint(patient, doctor)`. Deleting a patient
  or doctor removes their mappings (cascade).
- **Privacy:** other users' patients and mappings return 404 (not 403), and posting a foreign
  patient ID to `/api/mappings/` gives the same error as a nonexistent one.
- **Errors:** a central exception handler returns the uniform JSON shape above; database
  and unexpected errors are logged on the server and answered with a generic message.
- Extra, not required: `POST /api/auth/token/refresh/`, `PATCH` on patients/doctors, Django admin.

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `ImproperlyConfigured: Missing required environment variable ...` | Create `.env` from `.env.example` in the project root (next to `manage.py`) and fill in all values. |
| `connection refused` / `could not connect to server` | PostgreSQL is not running or the host/port is wrong. Linux: `sudo systemctl start postgresql`. Windows: start the *postgresql-x64-NN* service in Services. |
| `password authentication failed for user` | `DB_USER`/`DB_PASSWORD` in `.env` do not match what you created in `psql`. Reset: `ALTER USER healthcare_user WITH PASSWORD '...';` |
| `database "healthcare_db" does not exist` | Run the `CREATE DATABASE` step in section 4. |
| `permission denied to create database` when running tests | `ALTER USER healthcare_user CREATEDB;` as the `postgres` superuser. |
| `permission denied for schema public` (PostgreSQL 15+) | As `postgres`: `\c healthcare_db` then `GRANT ALL ON SCHEMA public TO healthcare_user;` (creating the DB with `OWNER healthcare_user` normally avoids this). |
| `ModuleNotFoundError: No module named 'django'` | The virtual environment is not active; activate it and `pip install -r requirements.txt`. |
| `relation "users_user" does not exist` | Run `python manage.py migrate`. |
| Postman returns `401` on protected routes | Token missing, expired (30 min) or not prefixed `Bearer `. Log in again or use the refresh endpoint. |
| `400` with "already assigned" | The doctor is already mapped to that patient. |
| PowerShell: *running scripts is disabled* | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `Invalid HTTP_HOST header` | Add the host to `DJANGO_ALLOWED_HOSTS`. |

For deployment: set `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, real
`DJANGO_ALLOWED_HOSTS`, serve with gunicorn/uvicorn behind HTTPS, and run
`python manage.py check --deploy`.
