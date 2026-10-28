"""Shared helpers for the automated tests."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from doctors.models import Doctor
from mappings.models import PatientDoctorMapping
from patients.models import Patient

User = get_user_model()

PASSWORD = "StrongPass#2026"


def make_user(email="alice@example.com", name="Alice", password=PASSWORD):
    return User.objects.create_user(email=email, password=password, name=name)


def login_client(email="alice@example.com", password=PASSWORD):
    """Return an APIClient authenticated through the real /login/ endpoint."""
    client = APIClient()
    response = client.post("/api/auth/login/", {"email": email, "password": password})
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


def patient_payload(**overrides):
    data = {
        "name": "John Doe",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "contact_number": "+91 98765 43210",
        "address": "12 Park Street, Delhi",
        "medical_history": "Mild asthma",
    }
    data.update(overrides)
    return data


def doctor_payload(**overrides):
    data = {
        "name": "Meera Sharma",
        "specialization": "Cardiology",
        "email": "meera.sharma@example.com",
        "contact_number": "+91 91234 56789",
        "years_of_experience": 12,
    }
    data.update(overrides)
    return data


class BaseAPITestCase(APITestCase):
    """Two users (alice, bob), each with an authenticated client."""

    def setUp(self):
        self.alice = make_user("alice@example.com", "Alice")
        self.bob = make_user("bob@example.com", "Bob")
        self.alice_client = login_client("alice@example.com")
        self.bob_client = login_client("bob@example.com")
        self.anonymous = APIClient()

    # Direct ORM helpers keep the tests for one app independent of the others.
    def create_patient(self, owner, **overrides):
        data = patient_payload(**overrides)
        return Patient.objects.create(owner=owner, **data)

    def create_doctor(self, creator, **overrides):
        data = doctor_payload(**overrides)
        return Doctor.objects.create(created_by=creator, **data)

    def create_mapping(self, patient, doctor):
        return PatientDoctorMapping.objects.create(patient=patient, doctor=doctor)
