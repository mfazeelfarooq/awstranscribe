from django.db import models

class AudioFile(models.Model):
    file = models.FileField(upload_to='audio/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Audio File {self.id}"

class TranscriptionResult(models.Model):
    audio_file = models.ForeignKey(AudioFile, on_delete=models.CASCADE)
    transcription = models.TextField()
    medical_entities = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Transcription for Audio {self.audio_file.id}" 