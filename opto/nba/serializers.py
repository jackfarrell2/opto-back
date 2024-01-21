from rest_framework import serializers
from .models import Slate

class SlateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slate
        fields = '__all__'