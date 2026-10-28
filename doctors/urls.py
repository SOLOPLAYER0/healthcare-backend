from django.urls import path

from .views import DoctorDetailView, DoctorListCreateView

urlpatterns = [
    path("", DoctorListCreateView.as_view(), name="doctor-list"),
    path("<int:pk>/", DoctorDetailView.as_view(), name="doctor-detail"),
]
