"""S3/MinIO storage service."""
import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

settings = get_settings()

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.s3_region,
)


def ensure_bucket():
    """Create bucket if it doesn't exist."""
    try:
        s3_client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        s3_client.create_bucket(Bucket=settings.s3_bucket)


def generate_presigned_upload(key: str, content_type: str = "audio/wav", expires: int = 3600) -> str:
    ensure_bucket()
    return s3_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def generate_presigned_download(key: str, expires: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )


def upload_fileobj(fileobj, key: str, content_type: str = "audio/wav"):
    ensure_bucket()
    s3_client.upload_fileobj(
        fileobj,
        settings.s3_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def object_exists(key: str) -> bool:
    try:
        s3_client.head_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except ClientError:
        return False


def delete_object(key: str) -> bool:
    """Hapus objek. Dipakai saat rekaman atau file cache dibuang."""
    try:
        s3_client.delete_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except ClientError:
        return False


def get_bytes(key: str) -> bytes | None:
    """Ambil isi objek, None kalau tidak ada."""
    try:
        return s3_client.get_object(Bucket=settings.s3_bucket, Key=key)["Body"].read()
    except ClientError:
        return None


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    ensure_bucket()
    s3_client.put_object(
        Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
    )
