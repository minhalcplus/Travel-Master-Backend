import os
import json
from google.cloud import storage
from uuid import uuid4
from fastapi import UploadFile
from core.app.env import settings

class GCSStorage:
    def __init__(self, bucket_name: str = None, credentials_path: str = "service_account.json"):
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        
        # Check if individual credentials are provided in env
        if settings.GCS_TYPE and settings.GCS_PRIVATE_KEY:
            try:
                credentials_info = {
                    "type": settings.GCS_TYPE,
                    "project_id": settings.GCS_PROJECT_ID,
                    "private_key_id": settings.GCS_PRIVATE_KEY_ID,
                    "private_key": settings.GCS_PRIVATE_KEY.replace('\\n', '\n') if settings.GCS_PRIVATE_KEY else None,
                    "client_email": settings.GCS_CLIENT_EMAIL,
                    "client_id": settings.GCS_CLIENT_ID,
                    "auth_uri": settings.GCS_AUTH_URI,
                    "token_uri": settings.GCS_TOKEN_URI,
                    "auth_provider_x509_cert_url": settings.GCS_AUTH_PROVIDER_X509_CERT_URL,
                    "client_x509_cert_url": settings.GCS_CLIENT_X509_CERT_URL,
                    "universe_domain": settings.GCS_UNIVERSE_DOMAIN
                }
                # Remove None values
                credentials_info = {k: v for k, v in credentials_info.items() if v is not None}
                
                self.client = storage.Client.from_service_account_info(credentials_info)
                print("✅ GCS storage initialized using individual environment variables")
            except Exception as e:
                print(f"❌ Failed to initialize GCS from individual env vars: {e}")
                self._init_from_file(credentials_path)
        else:
            self._init_from_file(credentials_path)

        self.bucket = self.client.bucket(self.bucket_name)

    def _init_from_file(self, credentials_path: str):
        config_path = os.path.join(os.getcwd(), credentials_path)
        if not os.path.exists(config_path):
             # Fallback if running from a different directory (sanity check)
             config_path = credentials_path
        
        if os.path.exists(config_path):
            self.client = storage.Client.from_service_account_json(config_path)
            print(f"✅ GCS storage initialized using service account file: {config_path}")
        else:
            # If no file and no env, this will likely fail later but we try to initialize with default auth
            # Or we can raise an error. GCS Client usually looks for GOOGLE_APPLICATION_CREDENTIALS env var.
            self.client = storage.Client()
            print("ℹ️ GCS storage initialized using default credentials")

    async def upload_file(self, file: UploadFile, directory: str = "events") -> str:
        """
        Uploads a file to GCS and returns the public URL.
        file: The FastAPI UploadFile object
        directory: The 'folder' in the bucket
        """
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{directory}/{uuid4()}{file_extension}"
        blob = self.bucket.blob(filename)
        
        # Read file content
        content = await file.read()
        blob.upload_from_string(content, content_type=file.content_type)
        
        # Reset cursor just in case it's used elsewhere (though usually consumed)
        await file.seek(0)
        
        return filename

    def delete_file(self, filename: str):
        """
        Deletes a file from GCS.
        filename: The blob name (e.g., 'events/abcd.jpg')
        """
        if not filename:
            return
        
        # In case the input is a full URL, try to extract the blob name.
        # This is basic and assumes the standard GCS public URL format.
        # https://storage.googleapis.com/BUCKET_NAME/BLOB_NAME
        # or custom domain. 
        # For now, we assume the database stores the 'blob name' or we handle the parsing.
        # If we store full URLs in DB, we need to parse.
        # Let's assume for now we might pass the full URL or just the name. 
        
        blob_name = filename
        if "storage.googleapis.com" in filename:
             parts = filename.split(f"/{self.bucket_name}/")
             if len(parts) > 1:
                 blob_name = parts[1]
        
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            blob.delete()

    def get_public_url(self, filename: str) -> str:
        """
        Returns the public URL for a given blob name.
        """
         # Ensure we don't double-wrap if it's already a URL
        if filename.startswith("http"):
            return filename
            
        return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"

# Singleton instance (optional, or instantiate where needed)
gcs_storage = GCSStorage()
