from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    created_by = serializers.IntegerField(source="created_by_id", read_only=True)

    class Meta:
        model = Doctor
        fields = (
            "id",
            "name",
            "specialization",
            "email",
            "contact_number",
            "years_of_experience",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")
        extra_kwargs = {
            "email": {
                "error_messages": {"unique": "A doctor with this email already exists."}
            },
        }

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name may not be blank.")
        return value

    def validate_specialization(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Specialization may not be blank.")
        return value

    def validate_years_of_experience(self, value):
        if value > 70:
            raise serializers.ValidationError("Years of experience is not realistic.")
        return value
