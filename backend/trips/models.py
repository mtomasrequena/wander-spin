import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at`` and ``updated_at`` fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Trip(TimeStampedModel):
    """
    Represents a travel plan created by a user and shared with collaborators.
    """
    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', _('Public')
        PRIVATE = 'PRIVATE', _('Private')
        UNLISTED = 'UNLISTED', _('Unlisted')

    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cover_image_url = models.URLField(max_length=500, blank=True, null=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        db_index=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_trips'
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TripCollaborator',
        related_name='shared_trips',
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Trip')
        verbose_name_plural = _('Trips')

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class TripCollaborator(models.Model):
    """
    Explicit through-table managing user permissions within a trip.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        EDITOR = 'EDITOR', _('Editor')
        VIEWER = 'VIEWER', _('Viewer')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trip_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['trip', 'user'],
                name='unique_trip_collaborator'
            )
        ]
        verbose_name = _('Trip Collaborator')
        verbose_name_plural = _('Trip Collaborators')

    def __str__(self):
        return f"{self.user.username} - {self.trip.title} [{self.role}]"


class PointOfInterest(TimeStampedModel):
    """
    Represents a single destination, stop, or venue linked to a trip.
    Supports both predictive Google Places data and manual URL entries.
    """
    class Category(models.TextChoices):
        ACCOMMODATION = 'ACCOMMODATION', _('Accommodation')
        FOOD_DRINK = 'FOOD_DRINK', _('Food & Drink')
        ATTRACTION = 'ATTRACTION', _('Attraction / Sightseeing')
        NATURE = 'NATURE', _('Nature & Outdoor')
        TRANSPORT = 'TRANSPORT', _('Transport / Hub')
        OTHER = 'OTHER', _('Other')

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='points_of_interest'
    )
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True
    )
    notes = models.TextField(blank=True, default='')

    # Hybrid location sourcing
    google_place_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Google Places API unique identifier")
    )
    source_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text=_("Fallback manual URL (e.g., blog post, Instagram link, direct map pin)")
    )
    formatted_address = models.CharField(max_length=500, blank=True, default='')

    # Geographic coordinates (Decimal precision for sub-meter GPS accuracy)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Order/Priority for routing and roulette features
    sequence_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order index for manual or AI-generated itineraries")
    )
    is_visited = models.BooleanField(default=False)

    class Meta:
        ordering = ['sequence_order', 'created_at']
        indexes = [
            models.Index(fields=['trip', 'sequence_order']),
        ]
        verbose_name = _('Point of Interest')
        verbose_name_plural = _('Points of Interest')

    def __str__(self):
        return f"{self.name} - {self.trip.title}"