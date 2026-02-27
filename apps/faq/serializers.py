from rest_framework import serializers
from .models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer", "order", "created_at")


class FAQCreateUpdateSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FAQ
        fields = ("question", "answer", "order", "created_at")
