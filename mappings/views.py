from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from patients.models import Patient

from .models import PatientDoctorMapping
from .serializers import MappingSerializer


def user_mappings(user):
    """All mappings that involve patients owned by `user`."""
    return PatientDoctorMapping.objects.filter(patient__owner=user).select_related(
        "patient", "doctor"
    )


class MappingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/mappings/ - all mappings for the caller's patients
    POST /api/mappings/ - assign a doctor to one of the caller's patients
    """

    serializer_class = MappingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return user_mappings(self.request.user)

    def perform_create(self, serializer):
        try:
            # The savepoint keeps the surrounding transaction usable if the
            # unique constraint fires (e.g. two simultaneous identical requests).
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"non_field_errors": ["This doctor is already assigned to this patient."]}
            )


class MappingDetailView(APIView):
    """
    /api/mappings/<id>/ has two meanings, as specified by the assignment:

    GET    - <id> is a PATIENT id: list every doctor assigned to that patient
    DELETE - <id> is a MAPPING id: remove that assignment
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk, owner=request.user)
        mappings = (
            PatientDoctorMapping.objects.filter(patient=patient)
            .select_related("patient", "doctor")
            .order_by("id")
        )
        return Response(MappingSerializer(mappings, many=True).data)

    def delete(self, request, pk):
        mapping = get_object_or_404(user_mappings(request.user), pk=pk)
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
