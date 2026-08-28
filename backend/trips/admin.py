from django.contrib import admin
from .models import Trip, TripCollaborator, PointOfInterest


class TripCollaboratorInline(admin.TabularInline):
    model = TripCollaborator
    extra = 1


class PointOfInterestInline(admin.StackedInline):
    model = PointOfInterest
    extra = 1


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'visibility', 'start_date', 'end_date', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('title', 'owner__username')
    inlines = [TripCollaboratorInline, PointOfInterestInline]


@admin.register(PointOfInterest)
class PointOfInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'trip', 'category', 'sequence_order', 'is_visited')
    list_filter = ('category', 'is_visited')
    search_fields = ('name', 'trip__title', 'google_place_id')