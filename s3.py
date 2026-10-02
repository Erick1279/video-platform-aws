import boto3
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-2")
BUCKET_VIDEOS = os.getenv("BUCKET_VIDEOS")
BUCKET_THUMBNAILS = os.getenv("BUCKET_THUMBNAILS")

s3_client = boto3.client("s3", region_name=REGION)

def upload_file_to_s3(file_bytes: bytes, filename: str, content_type: str, is_video: bool = True) -> str:
    bucket_name = BUCKET_VIDEOS if is_video else BUCKET_THUMBNAILS
    ext = filename.split(".")[-1]
    unique_key = f"{uuid.uuid4()}.{ext}"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=unique_key,
        Body=file_bytes,
        ContentType=content_type
    )
    
    # Retorna la URL pública directa del recurso
    return f"https://{bucket_name}.s3.{REGION}.amazonaws.com/{unique_key}"
