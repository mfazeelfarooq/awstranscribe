from django.views.generic import TemplateView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import AudioFile, TranscriptionResult
from .aws_utils import AWSServices
import uuid

class HomePageView(TemplateView):
    template_name = "medical_transcribe/home.html"

@method_decorator(csrf_exempt, name='dispatch')
class MedicalTranscribeViewSet(viewsets.ViewSet):
    aws_services = AWSServices()

    @action(detail=False, methods=['POST'])
    def upload_audio(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, 
                          status=status.HTTP_400_BAD_REQUEST)

        audio_file = request.FILES['file']
        
        try:
            # Save the audio file locally first
            audio_instance = AudioFile.objects.create(file=audio_file)
            
            # Generate unique job name
            job_name = f"medical-transcription-{uuid.uuid4()}"
            
            # Get the local file path
            file_path = audio_instance.file.path
            
            # Open the saved file and upload to S3
            with open(file_path, 'rb') as file_data:
                s3_uri = self.aws_services.upload_to_s3(file_data, f"{job_name}.wav")
            
            # Start transcription
            transcription_response = self.aws_services.start_transcription(s3_uri, job_name)
            
            return Response({
                'message': 'Audio uploaded and transcription started',
                'job_name': job_name,
                'audio_id': audio_instance.id
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['GET'], url_path='status')
    def status(self, request, pk=None):
        try:
            job_status = self.aws_services.get_transcription_status(pk)
            return Response(job_status)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 

    @action(detail=False, methods=['POST'], url_path='analyze_medical_text')
    def analyze_medical_text(self, request):
        """Analyze medical text using AWS Comprehend Medical"""
        try:
            text = request.data.get('text')
            print(f"Received text for analysis: {text}")  # Debug log
            
            if not text:
                return Response({
                    'error': 'No text provided',
                    'medical_entities': self.aws_services._get_empty_categories()
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get medical entities
            try:
                medical_entities = self.aws_services.get_medical_entities(text)
                print(f"Medical entities result: {medical_entities}")  # Debug log
            except Exception as e:
                print(f"Error getting medical entities: {str(e)}")
                import traceback
                traceback.print_exc()
                return Response({
                    'error': f"Error analyzing text: {str(e)}",
                    'medical_entities': self.aws_services._get_empty_categories()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Check if we got any entities
            has_entities = any(len(entities) > 0 for entities in medical_entities.values())
            
            if has_entities:
                return Response({
                    'medical_entities': medical_entities
                })
            else:
                return Response({
                    'message': 'No medical terms found',
                    'medical_entities': medical_entities
                })
            
        except Exception as e:
            print(f"Error in view: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e),
                'medical_entities': self.aws_services._get_empty_categories()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def format_medical_entities(self, entities):
        """Format medical entities for display"""
        categories = {
            'MEDICAL_CONDITION': [],
            'MEDICATION': [],
            'TEST_TREATMENT_PROCEDURE': [],
            'ANATOMY': [],
            'SYMPTOM': []
        }
        
        for entity in entities:
            category = entity.get('Category')
            if category in categories:
                categories[category].append({
                    'text': entity.get('Text'),
                    'type': entity.get('Type'),
                    'score': round(entity.get('Score', 0) * 100, 2),
                    'traits': [trait.get('Name') for trait in entity.get('Traits', [])]
                })
        
        return categories

    def format_phi_entities(self, entities):
        """Format PHI entities for display"""
        return [{
            'type': entity.get('Type'),
            'text': entity.get('Text'),
            'score': round(entity.get('Score', 0) * 100, 2)
        } for entity in entities]

    def format_icd10_entities(self, entities):
        """Format ICD-10 entities for display"""
        return [{
            'text': entity.get('Text'),
            'code': entity.get('ICD10CMConcepts', [{}])[0].get('Code'),
            'description': entity.get('ICD10CMConcepts', [{}])[0].get('Description'),
            'score': round(entity.get('Score', 0) * 100, 2)
        } for entity in entities]

    def format_rx_norm_entities(self, entities):
        """Format RxNorm entities for display"""
        return [{
            'text': entity.get('Text'),
            'code': entity.get('RxNormConcepts', [{}])[0].get('Code'),
            'description': entity.get('RxNormConcepts', [{}])[0].get('Description'),
            'score': round(entity.get('Score', 0) * 100, 2)
        } for entity in entities] 