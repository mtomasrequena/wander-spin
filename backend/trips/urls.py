from django.urls import path, include
from rest_framework_nested import routers
from .views import TripViewSet, TripCollaboratorViewSet, PointOfInterestViewSet

# 1. Main router for the trips endpoint
router = routers.DefaultRouter()
router.register(r'trips', TripViewSet, basename='trip')

# 2. Nested router for trip collaborators and POIs
# Generates routes like /trips/{trip_pk}/collaborators/ and /trips/{trip_pk}/pois/
trips_router = routers.NestedDefaultRouter(router, r'trips', lookup='trip')
trips_router.register(r'collaborators', TripCollaboratorViewSet, basename='trip-collaborator')
trips_router.register(r'pois', PointOfInterestViewSet, basename='trip-poi')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(trips_router.urls)),
]