# zoho_integration/serializers.py
from rest_framework import serializers

class ZohoRecordSerializer(serializers.Serializer):
    phone = serializers.CharField()
    owner = serializers.CharField(allow_null=True)
