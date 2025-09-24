from rest_framework import serializers
from django.core.exceptions import ImproperlyConfigured


class RestrictUpdateFieldsMixin:
    """
    A serializer mixin to restrict which fields can be updated.

    This mixin allows you to define either a whitelist (`updatable_fields`) or
    a blacklist (`non_updatable_fields`) in your serializer's `Meta` class to control
    which fields are allowed to be updated during PATCH/PUT operations.

    Usage:
        class MySerializer(RestrictUpdateFieldsMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = '__all__'
                updatable_fields = ['field1', 'field2']
                # OR
                # non_updatable_fields = ['readonly_field1', 'readonly_field2']

    Notes:
        - If both `updatable_fields` and `non_updatable_fields` are defined,
          an ImproperlyConfigured exception is raised.
        - Fields not in the allowed list will be silently ignored (not updated).
        - This mixin overrides the `update()` method but leaves `create()` untouched.

    Raises:
        ImproperlyConfigured: If both `updatable_fields` and `non_updatable_fields` are defined.
    """

    def update(self, instance, validated_data):
        meta = getattr(self, 'Meta', None)
        has_updatable = hasattr(meta, 'updatable_fields')
        has_non_updatable = hasattr(meta, 'non_updatable_fields')

        # Prevent misconfiguration
        if has_updatable and has_non_updatable:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__}: Do not set both 'updatable_fields' and "
                f"'non_updatable_fields' in Meta."
            )

        # Apply whitelist filtering
        if has_updatable:
            allowed_fields = set(meta.updatable_fields)
            validated_data = {
                key: value
                for key, value in validated_data.items()
                if key in allowed_fields
            }

        # Apply blacklist filtering
        elif has_non_updatable:
            disallowed_fields = set(meta.non_updatable_fields)
            validated_data = {
                key: value
                for key, value in validated_data.items()
                if key not in disallowed_fields
            }

        # Apply the updates
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
