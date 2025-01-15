from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicalTranscribeViewSet

router = DefaultRouter()
router.register(r'medical-transcribe', MedicalTranscribeViewSet, basename='medical-transcribe')

urlpatterns = [
    path('', include(router.urls)),
] 