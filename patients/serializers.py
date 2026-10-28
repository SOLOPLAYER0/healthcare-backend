from datetime import date

from django.utils import timezone
from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # Computed from date_of_birth; never accepted as input.
    age = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = (
            "id",
            "name",
            "date_of_birth",
            "age",
            "gender",
            "contact_number",
            "address",
            "medical_history",
            "created_at",
            "updated_at",
        )
        # `owner` is intentionally not exposed or writable: it is always the
        # authenticated user (set in the view).
        read_only_fields = ("id", "age", "created_at", "updated_at")

    def get_age(self, obj):
        today = date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name may not be blank.")
        return value

    def validate_address(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Address may not be blank.")
        return value

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if value.year < 1900:
            raise serializers.ValidationError("Date of birth is not realistic.")
        return value
