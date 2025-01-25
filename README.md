# Medical Transcription and Entity Extraction

## Overview
This project uses AWS services to perform:

1. File Uploads to Amazon S3
2. Medical Transcription using Amazon Transcribe Medical
3. Entity Extraction using Amazon Comprehend Medical

It provides a Python-based implementation to:
- Upload audio files to S3.
- Start transcription jobs and fetch transcription results.
- Extract medical entities like symptoms, medications, and diagnoses.

---

## Features

### 1. Amazon S3 Integration**
- Upload audio files to a specified S3 bucket.
- Verify the upload by checking the file's presence and size.

### 2. Amazon Transcribe Medical Integration
- Start a medical transcription job for an audio file stored in S3.
- Check the status of the transcription job.
- Retrieve transcription results.

### 3. Amazon Comprehend Medical Integration
- Extract medical entities (e.g., symptoms, diagnoses, medications) from transcribed text.
- Categorize entities into:
  - `MEDICAL_CONDITION`
  - `MEDICATION`
  - `TEST_TREATMENT_PROCEDURE`
  - `ANATOMY`
  - `SYMPTOM`
- Detect additional information, such as:
  - Protected Health Information (PHI)
  - ICD-10 codes
  - RxNorm codes

---

## Prerequisites

### AWS Setup

1. Create an S3 Bucket
   - Use the [Amazon S3 Console](https://console.aws.amazon.com/s3) to create a bucket.
   - Note the bucket name for configuration.

2. Enable Amazon Transcribe Medical
   - Ensure Amazon Transcribe Medical is available in your AWS region.

3. Enable Amazon Comprehend Medical
   - Confirm Amazon Comprehend Medical is active in your AWS region.

4. IAM Permissions
   - Grant the following permissions to your IAM user or role:
     ```json
     {
       "Effect": "Allow",
       "Action": [
         "s3:PutObject",
         "s3:GetObject",
         "s3:ListBucket",
         "transcribe:StartMedicalTranscriptionJob",
         "transcribe:GetMedicalTranscriptionJob",
         "comprehendmedical:DetectEntitiesV2",
         "comprehendmedical:DetectPHI",
         "comprehendmedical:InferICD10CM",
         "comprehendmedical:InferRxNorm"
       ],
       "Resource": "*"
     }
     ```

### Python Environment

1. Install Python
   Ensure Python 3.7 or above is installed.

2. Install Required Libraries
   Use `pip` to install the required libraries:
   ```bash
   pip install boto3
   ```

3. Set Up AWS Credentials
   Configure AWS credentials using environment variables or an `.env` file:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key-id
   export AWS_SECRET_ACCESS_KEY=your-secret-access-key
   export AWS_REGION=your-region
   ```

   Alternatively, create a `.env` file in the project root:
   ```
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   AWS_REGION=your-region
   AWS_S3_BUCKET_NAME=your-s3-bucket-name
   ```
   Install `python-dotenv` to load environment variables:
   ```bash
   pip install python-dotenv
   ```

---

## How to Use

### 1. Initialize the AWSServices Class
```python
from aws_services import AWSServices
aws_services = AWSServices()
```

### 2. Upload a File to S3
```python
with open('example.wav', 'rb') as file:
    s3_uri = aws_services.upload_to_s3(file, 'example.wav')
    print(f"File uploaded to: {s3_uri}")
```

### 3. Start a Transcription Job
```python
response = aws_services.start_transcription(s3_uri, 'example-job')
print(response)
```

### 4. Check Transcription Status
```python
status = aws_services.get_transcription_status('example-job')
print(status)
```

### 5. Extract Medical Entities
```python
text = "Patient complains of fever and cough."
entities = aws_services.get_medical_entities(text)
print(entities)
```

### 6. Additional Analysis
#### Detect PHI
```python
phi = aws_services.detect_phi(text)
print(phi)
```

#### Detect ICD-10 Codes
```python
icd10 = aws_services.detect_icd10(text)
print(icd10)
```

#### Detect RxNorm Codes
```python
rx_norm = aws_services.detect_rx_norm(text)
print(rx_norm)
```

---

## Error Handling
The class includes basic error handling:
- File Upload: Verifies file size and S3 upload.
- Transcription: Ensures the S3 file exists and handles job failures.
- Entity Extraction: Handles AWS API errors and categorizes entities.

---

---

---

## License
This project is licensed under the MIT License.

