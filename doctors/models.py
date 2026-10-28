from django.conf import settings
from django.db import models

from patients.models import phone_validator


class Doctor(models.Model):
    # Creator of the record; only the creator may modify or delete it.
    # SET_NULL keeps the doctor (and any mappings) if the creator's account
    # is removed; such records become read-only for everybody except admins.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="doctors_created",
    )
    name = models.CharField(max_length=150)
    specialization = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=20, validators=[phone_validator])
    # Additional (optional) field beyond the basics.
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"
