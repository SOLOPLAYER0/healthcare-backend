from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Patient
from .serializers import PatientSerializer


class PatientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/patients/  - list the authenticated user's patients
    POST /api/patients/  - create a patient owned by the authenticated user
    """

    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Patient.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE /api/patients/<id>/

    The queryset is restricted to the caller's own patients, so another
    user's record (or a nonexistent ID) is simply a 404. Existence of other
    users' records is not revealed.
    """

    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Patient.objects.filter(owner=self.request.user)
