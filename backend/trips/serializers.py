# trips/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Trip, TripCollaborator, PointOfInterest

User = get_user_model()


class PointOfInterestSerializer(serializers.ModelSerializer):
    trip = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PointOfInterest
        fields = [
            'id', 'trip', 'name', 'category', 'notes',
            'google_place_id', 'source_url', 'formatted_address',
            'latitude', 'longitude', 'sequence_order', 'is_visited',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'trip', 'created_at', 'updated_at']

    def validate(self, attrs):
        google_place_id = attrs.get(
            'google_place_id',
            getattr(self.instance, 'google_place_id', None)
        )
        source_url = attrs.get(
            'source_url',
            getattr(self.instance, 'source_url', None)
        )
        if not google_place_id and not source_url:
            raise serializers.ValidationError(
                _lazy_error()
            )
        return attrs


def _lazy_error():
    from django.utils.translation import gettext_lazy as _
    return _("Provide either a google_place_id or a source_url.")


class TripCollaboratorSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TripCollaborator
        fields = [
            'id', 'trip', 'user', 'user_username', 'role', 'joined_at',
        ]
        read_only_fields = ['id', 'trip', 'joined_at']
        validators = []  # unique_together handled explicitly below

    def validate(self, attrs):
        trip = attrs.get('trip') or getattr(self.instance, 'trip', None)
        user = attrs.get('user') or getattr(self.instance, 'user', None)

        if trip and user:
            qs = TripCollaborator.objects.filter(trip=trip, user=user)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"user": "This user is already a collaborator on this trip."}
                )

        request = self.context.get('request')
        if trip and request and trip.owner_id == user.id if user else False:
            raise serializers.ValidationError(
                {"user": "The trip owner cannot be added as a collaborator."}
            )
        return attrs


class TripSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    points_of_interest = PointOfInterestSerializer(many=True, read_only=True)
    collaborators_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'cover_image_url', 'visibility', 'owner', 'owner_username',
            'collaborators_count', 'points_of_interest',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_collaborators_count(self, obj):
        return obj.memberships.count()

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "end_date cannot be earlier than start_date."}
            )
        return attrs


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints — avoids nested POI overhead."""
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    poi_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id', 'title', 'start_date', 'end_date', 'cover_image_url',
            'visibility', 'owner', 'owner_username', 'poi_count', 'created_at',
        ]
        read_only_fields = fields

    def get_poi_count(self, obj):
        return getattr(obj, 'poi_count', obj.points_of_interest.count())