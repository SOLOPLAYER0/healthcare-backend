from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Doctor
from .permissions import IsCreatorOrReadOnly
from .serializers import DoctorSerializer


class DoctorListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/doctors/ - list all doctors (any authenticated user)
    POST /api/doctors/ - create a doctor, recorded against the caller
    """

    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET             - any authenticated user
    PUT/PATCH/DELETE - only the user who created the doctor (403 otherwise)
    """

    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsCreatorOrReadOnly]
