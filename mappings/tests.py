from config.testing import BaseAPITestCase
from mappings.models import PatientDoctorMapping

LIST_URL = "/api/mappings/"


def detail_url(pk):
    return f"/api/mappings/{pk}/"


class MappingSetupMixin:
    def setUp(self):
        super().setUp()
        self.patient = self.create_patient(self.alice)
        self.doctor = self.create_doctor(self.alice, email="d1@example.com")
        self.doctor2 = self.create_doctor(self.bob, email="d2@example.com", name="Raj Patel")
        self.bobs_patient = self.create_patient(self.bob, name="Bob's Patient")


class MappingCreateTests(MappingSetupMixin, BaseAPITestCase):
    def test_assign_doctor_to_own_patient(self):
        response = self.alice_client.post(
            LIST_URL, {"patient": self.patient.pk, "doctor": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(response.data["doctor"]["id"], self.doctor.pk)
        self.assertEqual(response.data["doctor"]["specialization"], "Cardiology")
        self.assertTrue(
            PatientDoctorMapping.objects.filter(
                patient=self.patient, doctor=self.doctor
            ).exists()
        )

    def test_can_assign_doctor_created_by_another_user(self):
        response = self.alice_client.post(
            LIST_URL, {"patient": self.patient.pk, "doctor": self.doctor2.pk}
        )
        self.assertEqual(response.status_code, 201)

    def test_same_doctor_can_serve_multiple_patients(self):
        second = self.create_patient(self.alice, name="Second")
        self.alice_client.post(LIST_URL, {"patient": self.patient.pk, "doctor": self.doctor.pk})
        response = self.alice_client.post(
            LIST_URL, {"patient": second.pk, "doctor": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 201)

    def test_duplicate_assignment_rejected(self):
        payload = {"patient": self.patient.pk, "doctor": self.doctor.pk}
        self.assertEqual(self.alice_client.post(LIST_URL, payload).status_code, 201)
        response = self.alice_client.post(LIST_URL, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PatientDoctorMapping.objects.count(), 1)

    def test_cannot_assign_to_other_users_patient(self):
        response = self.alice_client.post(
            LIST_URL, {"patient": self.bobs_patient.pk, "doctor": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"]["patient"], ["Patient not found."])
        self.assertEqual(PatientDoctorMapping.objects.count(), 0)

    def test_other_users_patient_error_matches_nonexistent_patient(self):
        other = self.alice_client.post(
            LIST_URL, {"patient": self.bobs_patient.pk, "doctor": self.doctor.pk}
        )
        missing = self.alice_client.post(
            LIST_URL, {"patient": 999999, "doctor": self.doctor.pk}
        )
        self.assertEqual(other.data, missing.data)

    def test_nonexistent_doctor(self):
        response = self.alice_client.post(
            LIST_URL, {"patient": self.patient.pk, "doctor": 999999}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"]["doctor"], ["Doctor not found."])

    def test_missing_fields(self):
        response = self.alice_client.post(LIST_URL, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("patient", response.data["errors"])
        self.assertIn("doctor", response.data["errors"])

    def test_non_integer_ids(self):
        response = self.alice_client.post(LIST_URL, {"patient": "abc", "doctor": "xyz"})
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_create(self):
        response = self.anonymous.post(
            LIST_URL, {"patient": self.patient.pk, "doctor": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 401)


class MappingReadTests(MappingSetupMixin, BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.mapping = self.create_mapping(self.patient, self.doctor)
        self.bobs_mapping = self.create_mapping(self.bobs_patient, self.doctor2)

    def test_list_only_own_patients_mappings(self):
        response = self.alice_client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["id"] for m in response.data], [self.mapping.pk])

    def test_list_contains_nested_details(self):
        item = self.alice_client.get(LIST_URL).data[0]
        self.assertEqual(item["patient"]["name"], "John Doe")
        self.assertEqual(item["doctor"]["name"], "Meera Sharma")

    def test_get_doctors_for_patient(self):
        self.create_mapping(self.patient, self.doctor2)
        response = self.alice_client.get(detail_url(self.patient.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {m["doctor"]["id"] for m in response.data}, {self.doctor.pk, self.doctor2.pk}
        )

    def test_get_doctors_for_patient_without_assignments(self):
        fresh = self.create_patient(self.alice, name="Fresh")
        response = self.alice_client.get(detail_url(fresh.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_cannot_view_other_users_patient_mappings(self):
        response = self.alice_client.get(detail_url(self.bobs_patient.pk))
        self.assertEqual(response.status_code, 404)

    def test_get_for_nonexistent_patient(self):
        self.assertEqual(self.alice_client.get(detail_url(999999)).status_code, 404)

    def test_unauthenticated_read(self):
        self.assertEqual(self.anonymous.get(LIST_URL).status_code, 401)
        self.assertEqual(self.anonymous.get(detail_url(self.patient.pk)).status_code, 401)


class MappingDeleteTests(MappingSetupMixin, BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.mapping = self.create_mapping(self.patient, self.doctor)
        self.bobs_mapping = self.create_mapping(self.bobs_patient, self.doctor2)

    def test_delete_own_mapping(self):
        response = self.alice_client.delete(detail_url(self.mapping.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=self.mapping.pk).exists())
        # Patient and doctor themselves remain.
        self.patient.refresh_from_db()
        self.doctor.refresh_from_db()

    def test_cannot_delete_other_users_mapping(self):
        response = self.alice_client.delete(detail_url(self.bobs_mapping.pk))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PatientDoctorMapping.objects.filter(pk=self.bobs_mapping.pk).exists())

    def test_delete_nonexistent(self):
        self.assertEqual(self.alice_client.delete(detail_url(999999)).status_code, 404)

    def test_unauthenticated_delete(self):
        self.assertEqual(self.anonymous.delete(detail_url(self.mapping.pk)).status_code, 401)

    def test_can_reassign_after_delete(self):
        self.alice_client.delete(detail_url(self.mapping.pk))
        response = self.alice_client.post(
            LIST_URL, {"patient": self.patient.pk, "doctor": self.doctor.pk}
        )
        self.assertEqual(response.status_code, 201)

    def test_deleting_patient_removes_mappings(self):
        self.alice_client.delete(f"/api/patients/{self.patient.pk}/")
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=self.mapping.pk).exists())

    def test_deleting_doctor_removes_mappings(self):
        self.alice_client.delete(f"/api/doctors/{self.doctor.pk}/")
        self.assertFalse(PatientDoctorMapping.objects.filter(pk=self.mapping.pk).exists())

    def test_unsupported_methods(self):
        self.assertEqual(self.alice_client.put(detail_url(self.mapping.pk), {}).status_code, 405)
