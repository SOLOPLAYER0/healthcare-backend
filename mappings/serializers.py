from rest_framework import serializers

from doctors.models import Doctor
from patients.models import Patient

from .models import PatientDoctorMapping


class PatientSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ("id", "name", "gender", "date_of_birth", "contact_number")
        read_only_fields = fields


class DoctorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ("id", "name", "specialization", "email", "contact_number")
        read_only_fields = fields


class MappingSerializer(serializers.ModelSerializer):
    """
    Input:  {"patient": <patient id>, "doctor": <doctor id>}
    Output: the mapping with nested patient and doctor details.
    """

    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.none(),
        error_messages={
            "does_not_exist": "Patient not found.",
            "incorrect_type": "Patient id must be an integer.",
            "required": "This field is required.",
            "null": "This field may not be null.",
        },
    )
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        error_messages={
            "does_not_exist": "Doctor not found.",
            "incorrect_type": "Doctor id must be an integer.",
            "required": "This field is required.",
            "null": "This field may not be null.",
        },
    )

    class Meta:
        model = PatientDoctorMapping
        fields = ("id", "patient", "doctor", "assigned_at")
        read_only_fields = ("id", "assigned_at")
        # Duplicate check is done in validate() for a clearer message.
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            # Only the caller's own patients can be used. A patient owned by
            # someone else gets the same "Patient not found." error as a
            # nonexistent ID, so ownership of other IDs is not revealed.
            self.fields["patient"].queryset = Patient.objects.filter(owner=request.user)

    def validate(self, attrs):
        if PatientDoctorMapping.objects.filter(
            patient=attrs["patient"], doctor=attrs["doctor"]
        ).exists():
            raise serializers.ValidationError(
                "This doctor is already assigned to this patient."
            )
        return attrs

    def to_representation(self, instance):
        return {
            "id": instance.pk,
            "patient": PatientSummarySerializer(instance.patient).data,
            "doctor": DoctorSummarySerializer(instance.doctor).data,
            "assigned_at": serializers.DateTimeField().to_representation(instance.assigned_at),
        }
