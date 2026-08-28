# trips/permissions.py
from rest_framework import permissions
from .models import Trip, TripCollaborator


SAFE_ROLES_FOR_EDIT = (TripCollaborator.Role.ADMIN, TripCollaborator.Role.EDITOR)


def _get_trip(obj):
    """Resolve the parent Trip regardless of whether obj is a Trip or a related model."""
    return obj if isinstance(obj, Trip) else getattr(obj, 'trip', None)


class IsTripOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission: only the trip owner can perform unsafe
    operations (update/delete). Anyone with read access may pass GET/HEAD/OPTIONS,
    subject to the view's queryset already filtering visibility.
    """
    message = "Only the trip owner can perform this action."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        trip = _get_trip(obj)
        if trip is None:
            return False
        return trip.owner_id == request.user.id


class IsCollaboratorWithEditRights(permissions.BasePermission):
    """
    Grants write access to the trip owner, and to collaborators whose
    role is ADMIN or EDITOR. VIEWER-role collaborators are read-only.
    Unauthenticated users are denied entirely (paired with IsAuthenticated
    at the view level).
    """
    message = "You must be the trip owner or an editor/admin collaborator to perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        trip = _get_trip(obj)
        if trip is None:
            return False

        if request.method in permissions.SAFE_METHODS:
            if trip.owner_id == request.user.id:
                return True
            return TripCollaborator.objects.filter(
                trip=trip, user=request.user
            ).exists()

        if trip.owner_id == request.user.id:
            return True

        return TripCollaborator.objects.filter(
            trip=trip, user=request.user, role__in=SAFE_ROLES_FOR_EDIT
        ).exists()