from rest_framework import serializers

from reviews.models import Review

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.first_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "user_email",
            "rating",
            "comment",
            "created_at",
            "updated_at",
            "is_owner",
        ]
        read_only_fields = [
            "id",
            "user_name",
            "user_email",
            "created_at",
            "updated_at",
            "is_owner",
        ]

    def get_is_owner(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False
