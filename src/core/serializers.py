"""Serializers for all models."""
from rest_framework import serializers

from . models import Scene, Schedule, SolarSchedule, Unit


class UnitSerializer(serializers.ModelSerializer):
    """Serializer for Unit models."""

    class Meta:
        """Serializer options."""

        model = Unit
        fields = '__all__'


class SceneSerializer(serializers.ModelSerializer):
    """Serializer for Scene models."""

    class Meta:
        """Serializer options."""

        model = Scene
        fields = '__all__'

    units = serializers.SlugRelatedField(queryset=Unit.objects.all(), many=True,
                                         slug_field='slug')


class ScheduleSerializer(serializers.ModelSerializer):
    """Serializer for Schedule models."""

    class Meta:
        """Serializer options."""

        model = Schedule
        fields = '__all__'


class SolarScheduleSerializer(serializers.ModelSerializer):
    """Serializer for SolarSchedule models."""

    class Meta:
        """Serializer options."""

        model = SolarSchedule
        fields = '__all__'


class CommandSerializer(serializers.Serializer):
    """Serializer for sending commands."""

    action = serializers.ChoiceField(choices=Unit.ACTION_CHOICES)
    multiplier = serializers.IntegerField(min_value=1, max_value=16, default=1)
