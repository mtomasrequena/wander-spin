# trips/views.py
from django.db.models import Q, Count
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Trip, TripCollaborator, PointOfInterest
from .serializers import (
    TripSerializer,
    TripListSerializer,
    TripCollaboratorSerializer,
    PointOfInterestSerializer,
)
from .permissions import IsTripOwnerOrReadOnly, IsCollaboratorWithEditRights


class TripViewSet(viewsets.ModelViewSet):
    """
    CRUD for Trips. Visibility rules:
      - PUBLIC trips are visible to anyone.
      - PRIVATE/UNLISTED trips are visible only to the owner and collaborators.
    Write access is restricted to the owner (see IsTripOwnerOrReadOnly).
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsTripOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return TripListSerializer
        return TripSerializer

    def get_queryset(self):
        user = self.request.user
        base_qs = Trip.objects.select_related('owner').annotate(
            poi_count=Count('points_of_interest', distinct=True)
        )

        if user.is_authenticated:
            qs = base_qs.filter(
                Q(visibility=Trip.Visibility.PUBLIC)
                | Q(owner=user)
                | Q(memberships__user=user)
            ).distinct()
        else:
            qs = base_qs.filter(visibility=Trip.Visibility.PUBLIC)

        if self.action == 'retrieve':
            qs = qs.prefetch_related('points_of_interest')

        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], url_path='collaborators')
    def add_collaborator(self, request, pk=None):
        """
        Add a collaborator to a trip. Restricted to the trip owner.
        POST body: {"user": <user_id>, "role": "EDITOR"}
        """
        trip = self.get_object()
        if trip.owner_id != request.user.id:
            raise PermissionDenied("Only the trip owner can manage collaborators.")

        serializer = TripCollaboratorSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(trip=trip)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TripCollaboratorViewSet(viewsets.ModelViewSet):
    """
    Manage collaborator memberships for a given trip.
    Nested under a trip via URL kwarg `trip_pk`.
    Only the trip owner may create/update/delete memberships.
    """
    serializer_class = TripCollaboratorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_trip(self):
        return Trip.objects.get(pk=self.kwargs['trip_pk'])

    def get_queryset(self):
        return TripCollaborator.objects.filter(
            trip_id=self.kwargs['trip_pk']
        ).select_related('user', 'trip')

    def _assert_owner(self, trip):
        if trip.owner_id != self.request.user.id:
            raise PermissionDenied("Only the trip owner can manage collaborators.")

    def perform_create(self, serializer):
        trip = self.get_trip()
        self._assert_owner(trip)
        serializer.save(trip=trip)

    def perform_update(self, serializer):
        trip = self.get_trip()
        self._assert_owner(trip)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_owner(instance.trip)
        instance.delete()


class PointOfInterestViewSet(viewsets.ModelViewSet):
    """
    CRUD for Points of Interest. Nested under a trip via URL kwarg `trip_pk`.
    Write access requires owner or ADMIN/EDITOR collaborator role
    (see IsCollaboratorWithEditRights). Read access follows trip visibility.
    """
    serializer_class = PointOfInterestSerializer
    permission_classes = [permissions.IsAuthenticated, IsCollaboratorWithEditRights]

    def get_trip(self):
        trip = Trip.objects.select_related('owner').get(pk=self.kwargs['trip_pk'])
        user = self.request.user

        is_visible = (
            trip.visibility == Trip.Visibility.PUBLIC
            or trip.owner_id == user.id
            or TripCollaborator.objects.filter(trip=trip, user=user).exists()
        )
        if not is_visible:
            raise PermissionDenied("You do not have access to this trip.")
        return trip

    def get_queryset(self):
        trip = self.get_trip()
        return PointOfInterest.objects.filter(trip=trip).select_related('trip')

    def perform_create(self, serializer):
        trip = self.get_trip()
        # has_object_permission is not triggered on create (no instance yet),
        # so we replicate the write-access check explicitly here.
        user = self.request.user
        is_editor = trip.owner_id == user.id or TripCollaborator.objects.filter(
            trip=trip, user=user,
            role__in=[TripCollaborator.Role.ADMIN, TripCollaborator.Role.EDITOR]
        ).exists()
        if not is_editor:
            raise PermissionDenied("You do not have edit rights on this trip.")
        serializer.save(trip=trip)