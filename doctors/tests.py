from config.testing import BaseAPITestCase, doctor_payload
from doctors.models import Doctor

LIST_URL = "/api/doctors/"


def detail_url(pk):
    return f"/api/doctors/{pk}/"


class DoctorCreateTests(BaseAPITestCase):
    def test_create_doctor(self):
        response = self.alice_client.post(LIST_URL, doctor_payload())
        self.assertEqual(response.status_code, 201)
        doctor = Doctor.objects.get(pk=response.data["id"])
        self.assertEqual(doctor.created_by, self.alice)
        self.assertEqual(response.data["created_by"], self.alice.pk)

    def test_created_by_cannot_be_spoofed(self):
        response = self.alice_client.post(LIST_URL, doctor_payload(created_by=self.bob.pk))
        self.assertEqual(Doctor.objects.get(pk=response.data["id"]).created_by, self.alice)

    def test_missing_fields(self):
        response = self.alice_client.post(LIST_URL, {})
        self.assertEqual(response.status_code, 400)
        for field in ("name", "specialization", "email", "contact_number"):
            self.assertIn(field, response.data["errors"])

    def test_invalid_email(self):
        response = self.alice_client.post(LIST_URL, doctor_payload(email="bad"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])

    def test_duplicate_email(self):
        self.alice_client.post(LIST_URL, doctor_payload())
        response = self.bob_client.post(LIST_URL, doctor_payload(name="Someone Else"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])

    def test_invalid_contact_number(self):
        response = self.alice_client.post(LIST_URL, doctor_payload(contact_number="x"))
        self.assertEqual(response.status_code, 400)

    def test_negative_experience_rejected(self):
        response = self.alice_client.post(LIST_URL, doctor_payload(years_of_experience=-1))
        self.assertEqual(response.status_code, 400)

    def test_unrealistic_experience_rejected(self):
        response = self.alice_client.post(LIST_URL, doctor_payload(years_of_experience=200))
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_create(self):
        response = self.anonymous.post(LIST_URL, doctor_payload())
        self.assertEqual(response.status_code, 401)


class DoctorReadTests(BaseAPITestCase):
    def test_any_authenticated_user_sees_all_doctors(self):
        d1 = self.create_doctor(self.alice, email="a@example.com")
        d2 = self.create_doctor(self.bob, email="b@example.com")
        response = self.alice_client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.data}, {d1.pk, d2.pk})

    def test_retrieve_other_users_doctor(self):
        doctor = self.create_doctor(self.bob)
        response = self.alice_client.get(detail_url(doctor.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["specialization"], "Cardiology")

    def test_retrieve_nonexistent(self):
        self.assertEqual(self.alice_client.get(detail_url(999999)).status_code, 404)

    def test_unauthenticated_read(self):
        doctor = self.create_doctor(self.alice)
        self.assertEqual(self.anonymous.get(LIST_URL).status_code, 401)
        self.assertEqual(self.anonymous.get(detail_url(doctor.pk)).status_code, 401)


class DoctorModifyTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.doctor = self.create_doctor(self.alice)

    def test_creator_can_update(self):
        response = self.alice_client.put(
            detail_url(self.doctor.pk),
            doctor_payload(name="Updated", specialization="Neurology"),
        )
        self.assertEqual(response.status_code, 200)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.name, "Updated")
        self.assertEqual(self.doctor.specialization, "Neurology")

    def test_update_keeping_own_email_is_allowed(self):
        response = self.alice_client.put(detail_url(self.doctor.pk), doctor_payload())
        self.assertEqual(response.status_code, 200)

    def test_update_to_another_doctors_email_rejected(self):
        self.create_doctor(self.alice, email="taken@example.com")
        response = self.alice_client.put(
            detail_url(self.doctor.pk), doctor_payload(email="taken@example.com")
        )
        self.assertEqual(response.status_code, 400)

    def test_creator_can_patch(self):
        response = self.alice_client.patch(detail_url(self.doctor.pk), {"name": "Patched"})
        self.assertEqual(response.status_code, 200)

    def test_non_creator_cannot_update(self):
        response = self.bob_client.put(
            detail_url(self.doctor.pk), doctor_payload(name="Hacked")
        )
        self.assertEqual(response.status_code, 403)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.name, "Meera Sharma")

    def test_non_creator_cannot_patch(self):
        response = self.bob_client.patch(detail_url(self.doctor.pk), {"name": "Hacked"})
        self.assertEqual(response.status_code, 403)

    def test_non_creator_cannot_delete(self):
        response = self.bob_client.delete(detail_url(self.doctor.pk))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Doctor.objects.filter(pk=self.doctor.pk).exists())

    def test_creator_can_delete(self):
        response = self.alice_client.delete(detail_url(self.doctor.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Doctor.objects.filter(pk=self.doctor.pk).exists())

    def test_update_nonexistent(self):
        response = self.alice_client.put(detail_url(999999), doctor_payload())
        self.assertEqual(response.status_code, 404)

    def test_delete_nonexistent(self):
        self.assertEqual(self.alice_client.delete(detail_url(999999)).status_code, 404)

    def test_unauthenticated_modify(self):
        self.assertEqual(
            self.anonymous.put(detail_url(self.doctor.pk), doctor_payload()).status_code, 401
        )
        self.assertEqual(self.anonymous.delete(detail_url(self.doctor.pk)).status_code, 401)

    def test_orphaned_doctor_is_read_only(self):
        """If the creator's account is deleted, nobody can modify the doctor."""
        self.alice.delete()
        self.doctor.refresh_from_db()
        self.assertIsNone(self.doctor.created_by)
        self.assertEqual(self.bob_client.delete(detail_url(self.doctor.pk)).status_code, 403)
