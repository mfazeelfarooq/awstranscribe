import boto3
import uuid
from django.conf import settings

class AWSServices:
    def __init__(self):
        self.s3_client = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.transcribe_client = boto3.client('transcribe',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.comprehend_medical = boto3.client('comprehendmedical',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    def upload_to_s3(self, file_obj, filename):
        try:
            # Verify file is not empty
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Reset to beginning
            
            if file_size == 0:
                raise Exception("File is empty")

            # Upload to S3
            self.s3_client.upload_fileobj(
                file_obj,
                settings.AWS_S3_BUCKET_NAME,
                f'uploads/{filename}'
            )
            
            # Verify upload was successful
            try:
                self.s3_client.head_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    Key=f'uploads/{filename}'
                )
            except Exception as e:
                raise Exception("File upload verification failed")

            return f's3://{settings.AWS_S3_BUCKET_NAME}/uploads/{filename}'
        except Exception as e:
            raise Exception(f"Error uploading to S3: {str(e)}")

    def start_transcription(self, s3_uri, job_name):
        try:
            # Verify the file exists in S3 and is not empty
            bucket = settings.AWS_S3_BUCKET_NAME
            key = s3_uri.split(f's3://{bucket}/')[1]
            
            try:
                head_response = self.s3_client.head_object(
                    Bucket=bucket,
                    Key=key
                )
                if head_response['ContentLength'] == 0:
                    raise Exception("S3 file is empty")
            except Exception as e:
                raise Exception(f"Error verifying S3 file: {str(e)}")

            # Start transcription job
            response = self.transcribe_client.start_medical_transcription_job(
                MedicalTranscriptionJobName=job_name,
                LanguageCode='en-US',
                MediaFormat='wav',  # Changed to wav format
                Media={'MediaFileUri': s3_uri},
                OutputBucketName=settings.AWS_S3_BUCKET_NAME,
                Specialty='PRIMARYCARE',
                Type='CONVERSATION',
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 2
                }
            )
            return response
        except Exception as e:
            raise Exception(f"Error starting transcription: {str(e)}")

    def get_medical_entities(self, text):
        """Extract medical entities using AWS Comprehend Medical API"""
        try:
            if not text:
                print("Empty text provided")
                return self._get_empty_categories()

            print(f"Analyzing text: {text}")  # Debug log
            
            try:
                # Call AWS Comprehend Medical API
                print("Making API call to AWS Comprehend Medical...")
                response = self.comprehend_medical.detect_entities_v2(
                    Text=text
                )
                print(f"Raw API Response: {response}")  # Debug log
                
                if 'Entities' not in response:
                    print("No 'Entities' in response")
                    return self._get_empty_categories()
                    
            except Exception as api_error:
                print(f"AWS API Error: {str(api_error)}")
                if 'AccessDeniedException' in str(api_error):
                    print("AWS Permissions Error - Please add ComprehendMedical permissions to your IAM user")
                elif 'UnrecognizedClientException' in str(api_error):
                    print("AWS Credentials Error - Please check your AWS credentials")
                return self._get_empty_categories()

            entities = response['Entities']
            print(f"Number of entities detected: {len(entities)}")
            print(f"Detected entities: {entities}")

            # Initialize categories
            categories = self._get_empty_categories()

            # Map AWS Comprehend Medical categories to our categories
            category_mapping = {
                'DIAGNOSIS': 'MEDICAL_CONDITION',
                'DX_NAME': 'MEDICAL_CONDITION',
                'MEDICAL_CONDITION': 'MEDICAL_CONDITION',
                'PROBLEM': 'MEDICAL_CONDITION',  # Added this
                'MEDICATION': 'MEDICATION',
                'GENERIC_NAME': 'MEDICATION',
                'BRAND_NAME': 'MEDICATION',
                'TEST_NAME': 'TEST_TREATMENT_PROCEDURE',
                'PROCEDURE_NAME': 'TEST_TREATMENT_PROCEDURE',
                'TREATMENT_NAME': 'TEST_TREATMENT_PROCEDURE',
                'ANATOMY': 'ANATOMY',
                'SYSTEM_ORGAN_SITE': 'ANATOMY',
                'BODY_PART': 'ANATOMY',
                'SIGN': 'SYMPTOM',
                'SYMPTOM': 'SYMPTOM'
            }

            # Process each entity
            for entity in entities:
                try:
                    entity_type = entity.get('Type')
                    category = category_mapping.get(entity_type)
                    print(f"Processing entity: Type={entity_type}, Category={category}")
                    
                    if category:
                        entity_data = {
                            'text': entity.get('Text', ''),
                            'type': entity_type,
                            'score': round(float(entity.get('Score', 0)) * 100, 2),
                            'traits': [trait.get('Name', '') for trait in entity.get('Traits', [])]
                        }
                        categories[category].append(entity_data)
                        print(f"Added entity to {category}: {entity_data}")
                except Exception as entity_error:
                    print(f"Error processing entity {entity}: {str(entity_error)}")
                    continue

            print(f"Final categories: {categories}")
            return categories

        except Exception as e:
            print(f"Error in medical entity extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._get_empty_categories()

    def _get_empty_categories(self):
        """Return empty category structure"""
        return {
            'MEDICAL_CONDITION': [],
            'MEDICATION': [],
            'TEST_TREATMENT_PROCEDURE': [],
            'ANATOMY': [],
            'SYMPTOM': []
        }

    def get_transcription_status(self, job_name):
        try:
            response = self.transcribe_client.get_medical_transcription_job(
                MedicalTranscriptionJobName=job_name
            )
            
            job = response['MedicalTranscriptionJob']
            status = job['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                try:
                    # Get the transcript file from S3
                    transcript_uri = job['Transcript']['TranscriptFileUri']
                    
                    # Parse the URI to get bucket and key
                    uri_parts = transcript_uri.replace('https://', '').split('/')
                    if '.s3.' in uri_parts[0]:  # virtual-hosted style URL
                        bucket = uri_parts[0].split('.s3.')[0]
                        key = '/'.join(uri_parts[1:])
                    else:  # path-style URL
                        bucket = uri_parts[1]
                        key = '/'.join(uri_parts[2:])
                    
                    # Get the transcript JSON file
                    response = self.s3_client.get_object(
                        Bucket=bucket,
                        Key=key
                    )
                    
                    import json
                    transcript_data = json.loads(response['Body'].read().decode('utf-8'))
                    
                    # Extract the transcription text
                    transcription_text = transcript_data['results']['transcripts'][0]['transcript']
                    
                    return {
                        'status': status,
                        'transcription': transcription_text,
                        'medical_entities': self.get_medical_entities(transcription_text)
                    }
                except Exception as e:
                    print(f"Error getting transcript: {str(e)}")
                    return {
                        'status': 'FAILED',
                        'error': f"Error retrieving transcript: {str(e)}"
                    }
            elif status == 'FAILED':
                return {
                    'status': status,
                    'error': job.get('FailureReason', 'Unknown error')
                }
            else:
                return {
                    'status': status
                }
        except Exception as e:
            raise Exception(f"Error checking transcription status: {str(e)}") 

    def analyze_medical_text(self, text):
        """Analyze medical text using multiple Comprehend Medical APIs"""
        try:
            print(f"Analyzing text: {text[:100]}...")  # Debug log
            # Use detect_medical_entities instead of get_medical_entities
            entities = self.detect_medical_entities(text)
            results = {
                'entities': entities,
                'phi': [],  # Simplified for now
                'icd10': [],
                'rx_norm': []
            }
            print(f"Analysis results: {results}")  # Debug log
            return results
        except Exception as e:
            print(f"Error in medical text analysis: {str(e)}")
            return None

    def detect_medical_entities(self, text):
        """Detect medical entities using Comprehend Medical"""
        try:
            print("Calling detect_entities_v2...")  # Debug log
            response = self.comprehend_medical.detect_entities_v2(Text=text)
            entities = response['Entities']
            print(f"Entities detected: {entities}")  # Debug log

            # Format entities into categories
            categories = {
                'MEDICAL_CONDITION': [],
                'MEDICATION': [],
                'TEST_TREATMENT_PROCEDURE': [],
                'ANATOMY': [],
                'SYMPTOM': []
            }

            category_mapping = {
                'DX_NAME': 'MEDICAL_CONDITION',
                'MEDICATION': 'MEDICATION',
                'TEST_NAME': 'TEST_TREATMENT_PROCEDURE',
                'PROCEDURE_NAME': 'TEST_TREATMENT_PROCEDURE',
                'ANATOMY': 'ANATOMY',
                'SYSTEM_ORGAN_SITE': 'ANATOMY',
                'SIGN': 'SYMPTOM',
                'SYMPTOM': 'SYMPTOM'
            }

            for entity in entities:
                category = category_mapping.get(entity.get('Type'))
                if category:
                    categories[category].append({
                        'text': entity.get('Text'),
                        'type': entity.get('Type'),
                        'score': round(entity.get('Score', 0) * 100, 2),
                        'traits': [trait.get('Name') for trait in entity.get('Traits', [])]
                    })

            return categories
        except Exception as e:
            print(f"Error detecting medical entities: {str(e)}")
            return {
                'MEDICAL_CONDITION': [],
                'MEDICATION': [],
                'TEST_TREATMENT_PROCEDURE': [],
                'ANATOMY': [],
                'SYMPTOM': []
            }

    def detect_phi(self, text):
        """Detect Protected Health Information"""
        try:
            response = self.comprehend_medical.detect_phi(Text=text)
            return response['Entities']
        except Exception as e:
            print(f"Error detecting PHI: {str(e)}")
            return []

    def detect_icd10(self, text):
        """Detect ICD-10 codes"""
        try:
            response = self.comprehend_medical.infer_icd10_cm(Text=text)
            return response['Entities']
        except Exception as e:
            print(f"Error detecting ICD-10 codes: {str(e)}")
            return []

    def detect_rx_norm(self, text):
        """Detect RxNorm codes"""
        try:
            response = self.comprehend_medical.infer_rx_norm(Text=text)
            return response['Entities']
        except Exception as e:
            print(f"Error detecting RxNorm codes: {str(e)}")
            return [] 