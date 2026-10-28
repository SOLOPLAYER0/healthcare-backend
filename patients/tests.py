from datetime import date, timedelta

from config.testing import BaseAPITestCase, patient_payload
from patients.models import Patient

LIST_URL = "/api/patients/"


def detail_url(pk):
    return f"/api/patients/{pk}/"


class PatientCreateTests(BaseAPITestCase):
    def test_create_patient_assigns_authenticated_user(self):
        response = self.alice_client.post(LIST_URL, patient_payload())
        self.assertEqual(response.status_code, 201)
        patient = Patient.objects.get(pk=response.data["id"])
        self.assertEqual(patient.owner, self.alice)
        self.assertIn("age", response.data)
        self.assertNotIn("owner", response.data)

    def test_owner_cannot_be_set_from_request_body(self):
        response = self.alice_client.post(
            LIST_URL, patient_payload(owner=self.bob.pk)
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Patient.objects.get(pk=response.data["id"]).owner, self.alice)

    def test_missing_required_fields(self):
        response = self.alice_client.post(LIST_URL, {})
        self.assertEqual(response.status_code, 400)
        for field in ("name", "date_of_birth", "gender", "contact_number", "address"):
            self.assertIn(field, response.data["errors"])

    def test_invalid_gender(self):
        response = self.alice_client.post(LIST_URL, patient_payload(gender="robot"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("gender", response.data["errors"])

    def test_future_date_of_birth(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        response = self.alice_client.post(LIST_URL, patient_payload(date_of_birth=future))
        self.assertEqual(response.status_code, 400)
        self.assertIn("date_of_birth", response.data["errors"])

    def test_invalid_date_format(self):
        response = self.alice_client.post(
            LIST_URL, patient_payload(date_of_birth="15/05/1990")
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_contact_number(self):
        response = self.alice_client.post(
            LIST_URL, patient_payload(contact_number="abc")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("contact_number", response.data["errors"])

    def test_blank_name(self):
        response = self.alice_client.post(LIST_URL, patient_payload(name="  "))
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_create(self):
        response = self.anonymous.post(LIST_URL, patient_payload())
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Patient.objects.count(), 0)


class PatientReadTests(BaseAPITestCase):
    def test_list_returns_only_own_patients(self):
        mine = self.create_patient(self.alice, name="Mine")
        self.create_patient(self.bob, name="Not Mine")
        response = self.alice_client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.data], [mine.pk])

    def test_list_empty(self):
        response = self.alice_client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_retrieve_own_patient(self):
        patient = self.create_patient(self.alice)
        response = self.alice_client.get(detail_url(patient.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "John Doe")

    def test_retrieve_nonexistent_patient(self):
        response = self.alice_client.get(detail_url(999999))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data["success"])

    def test_unauthenticated_list_and_detail(self):
        patient = self.create_patient(self.alice)
        self.assertEqual(self.anonymous.get(LIST_URL).status_code, 401)
        self.assertEqual(self.anonymous.get(detail_url(patient.pk)).status_code, 401)

    def test_non_numeric_id_is_404(self):
        self.assertEqual(self.alice_client.get("/api/patients/abc/").status_code, 404)


class PatientOwnershipTests(BaseAPITestCase):
    """Changing the ID in the URL must never expose another user's patient."""

    def setUp(self):
        super().setUp()
        self.bobs_patient = self.create_patient(self.bob, name="Bob's Patient")

    def test_cannot_retrieve_other_users_patient(self):
        response = self.alice_client.get(detail_url(self.bobs_patient.pk))
        self.assertEqual(response.status_code, 404)

    def test_cannot_update_other_users_patient(self):
        response = self.alice_client.put(
            detail_url(self.bobs_patient.pk), patient_payload(name="Hacked")
        )
        self.assertEqual(response.status_code, 404)
        self.bobs_patient.refresh_from_db()
        self.assertEqual(self.bobs_patient.name, "Bob's Patient")

    def test_cannot_patch_other_users_patient(self):
        response = self.alice_client.patch(
            detail_url(self.bobs_patient.pk), {"name": "Hacked"}
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_users_patient(self):
        response = self.alice_client.delete(detail_url(self.bobs_patient.pk))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Patient.objects.filter(pk=self.bobs_patient.pk).exists())

    def test_other_users_patient_looks_identical_to_missing(self):
        other = self.alice_client.get(detail_url(self.bobs_patient.pk))
        missing = self.alice_client.get(detail_url(999999))
        self.assertEqual(other.status_code, missing.status_code)
        self.assertEqual(other.data, missing.data)


class PatientUpdateDeleteTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.patient = self.create_patient(self.alice)

    def test_full_update(self):
        response = self.alice_client.put(
            detail_url(self.patient.pk),
            patient_payload(name="John Updated", gender="other", address="New Address"),
        )
        self.assertEqual(response.status_code, 200)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, "John Updated")
        self.assertEqual(self.patient.gender, "other")
        self.assertEqual(self.patient.owner, self.alice)

    def test_put_with_missing_fields_fails(self):
        response = self.alice_client.put(detail_url(self.patient.pk), {"name": "Only"})
        self.assertEqual(response.status_code, 400)

    def test_put_with_invalid_data(self):
        response = self.alice_client.put(
            detail_url(self.patient.pk), patient_payload(gender="x")
        )
        self.assertEqual(response.status_code, 400)

    def test_update_cannot_change_owner(self):
        self.alice_client.put(
            detail_url(self.patient.pk), patient_payload(owner=self.bob.pk)
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.owner, self.alice)

    def test_update_nonexistent(self):
        response = self.alice_client.put(detail_url(999999), patient_payload())
        self.assertEqual(response.status_code, 404)

    def test_delete_patient(self):
        response = self.alice_client.delete(detail_url(self.patient.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Patient.objects.filter(pk=self.patient.pk).exists())

    def test_delete_nonexistent(self):
        response = self.alice_client.delete(detail_url(999999))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_update_and_delete(self):
        self.assertEqual(
            self.anonymous.put(detail_url(self.patient.pk), patient_payload()).status_code, 401
        )
        self.assertEqual(self.anonymous.delete(detail_url(self.patient.pk)).status_code, 401)
