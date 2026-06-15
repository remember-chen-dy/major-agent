"""对象存储服务（MIMO）"""
import os
from datetime import datetime, timedelta
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from core.config import get_settings

settings = get_settings()


class StorageService:
    """MIMO 对象存储服务"""

    _client: Optional[boto3.client] = None

    @classmethod
    def _get_client(cls) -> boto3.client:
        """获取 S3 客户端"""
        if cls._client is None:
            cls._client = boto3.client(
                's3',
                endpoint_url=settings.MIMO_ENDPOINT,
                aws_access_key_id=settings.MIMO_ACCESS_KEY,
                aws_secret_access_key=settings.MIMO_SECRET_KEY,
                region_name='auto',
                config=Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'path'},
                    connect_timeout=3,
                    read_timeout=10,
                    retries={'max_attempts': 1},
                ),
            )
        return cls._client

    @classmethod
    async def upload_report(
        cls,
        user_id: str,
        session_id: str,
        pdf_content: bytes,
        timestamp: Optional[str] = None
    ) -> str:
        """上传报告到对象存储

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            pdf_content: PDF 文件内容
            timestamp: 时间戳（可选）

        Returns:
            预签名 URL
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_key = f"reports/{user_id}/{session_id}/{timestamp}.pdf"
        client = cls._get_client()

        try:
            cls.ensure_bucket()
            # 上传文件
            client.put_object(
                Bucket=settings.MIMO_BUCKET,
                Key=file_key,
                Body=pdf_content,
                ContentType='application/pdf',
            )

            # 生成预签名 URL（7 天有效期）
            presigned_url = cls.generate_presigned_url(file_key, expires_in=7)
            return presigned_url

        except ClientError as e:
            raise Exception(f"上传失败: {e}")

    @classmethod
    def ensure_bucket(cls) -> None:
        """确保报告 bucket 存在。"""
        client = cls._get_client()
        try:
            client.head_bucket(Bucket=settings.MIMO_BUCKET)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            client.create_bucket(Bucket=settings.MIMO_BUCKET)

    @classmethod
    def generate_presigned_url(cls, file_key: str, expires_in: int = 7) -> str:
        """生成预签名 URL

        Args:
            file_key: 文件 key
            expires_in: 有效期（天）

        Returns:
            预签名 URL
        """
        client = cls._get_client()

        try:
            url = client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.MIMO_BUCKET,
                    'Key': file_key,
                },
                ExpiresIn=expires_in * 24 * 60 * 60,  # 转换为秒
            )
            return url
        except ClientError as e:
            raise Exception(f"生成预签名 URL 失败: {e}")

    @classmethod
    async def download_report(cls, file_key: str) -> bytes:
        """下载报告

        Args:
            file_key: 文件 key

        Returns:
            文件内容
        """
        client = cls._get_client()

        try:
            response = client.get_object(
                Bucket=settings.MIMO_BUCKET,
                Key=file_key,
            )
            return response['Body'].read()
        except ClientError as e:
            raise Exception(f"下载失败: {e}")
