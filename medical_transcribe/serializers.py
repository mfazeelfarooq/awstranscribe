from rest_framework import serializers
from .models import AudioFile, TranscriptionResult

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['id', 'file', 'uploaded_at', 'transcription']

class TranscriptionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptionResult
        fields = ['id', 'audio_file', 'transcription', 'medical_entities', 'created_at'] 