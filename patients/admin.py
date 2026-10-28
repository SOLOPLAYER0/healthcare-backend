from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "gender", "owner", "created_at")
    list_filter = ("gender",)
    search_fields = ("name", "owner__email")
