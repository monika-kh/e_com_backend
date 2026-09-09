from rest_framework import serializers


class PlaceOrderSerializer(serializers.Serializer):
    """Input required to create an order from the authenticated user's cart."""

    address_id = serializers.IntegerField(min_value=1)
