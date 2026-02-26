from rest_framework import serializers
from .models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer", "order")


class FAQCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("question", "answer", "order")
