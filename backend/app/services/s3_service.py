import logging
import os
from io import BytesIO
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("medintel")


class S3Service:
    def __init__(self) -> None:
        self._local_storage = not settings.aws_access_key_id or settings.aws_access_key_id == "your-access-key"
        self.local_path = "./data/uploads"
        if self._local_storage:
            os.makedirs(self.local_path, exist_ok=True)
            logger.info("Using local file storage (S3 credentials not configured)")
        else:
            client_kwargs: dict = {
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
                "region_name": settings.aws_region,
            }
            if settings.s3_endpoint_url:
                client_kwargs["endpoint_url"] = settings.s3_endpoint_url
            self.client = boto3.client("s3", **client_kwargs)

    def upload_file(self, content: bytes, filename: str, content_type: str, folder: str = "uploads") -> tuple[str, str]:
        key = f"{folder}/{uuid4().hex}_{filename}"

        if self._local_storage:
            full_path = os.path.join(self.local_path, key.replace("/", os.sep))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)
            url = f"file://{os.path.abspath(full_path)}"
            return key, url

        self.client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        url = f"https://{settings.s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
        return key, url

    def download_file(self, key: str) -> bytes:
        if self._local_storage:
            full_path = os.path.join(self.local_path, key.replace("/", os.sep))
            with open(full_path, "rb") as f:
                return f.read()

        buffer = BytesIO()
        self.client.download_fileobj(settings.s3_bucket, key, buffer)
        return buffer.getvalue()

    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        if self._local_storage:
            full_path = os.path.join(self.local_path, key.replace("/", os.sep))
            return f"file://{os.path.abspath(full_path)}"

        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": key},
                ExpiresIn=expires,
            )
        except ClientError:
            return ""


s3_service = S3Service()
