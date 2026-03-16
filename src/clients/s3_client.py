import os
from pathlib import Path
from typing import List, Iterator

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


load_dotenv()


class S3AssetClient:
    """
    Lightweight asset client for streaming large files to and from S3.
    """

    def __init__(self):

        self.bucket = os.getenv("S3_API_KEY_NAME")
        access_key = os.getenv("S3_API_KEY_ACCESS_KEY")
        secret_key = os.getenv("S3_API_KEY_SECRET_ACCESS_KEY")

        if not all([self.bucket, access_key, secret_key]):
            raise RuntimeError("Missing S3 credentials in .env")

        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    # ------------------------------------------------
    # Upload
    # ------------------------------------------------

    def upload_all_assets(self, asset_dir: str = "assets") -> List[str]:
        """
        Upload all files in a directory to S3.
        Preserves directory structure.

        Returns uploaded object keys.
        """

        uploaded = []
        asset_path = Path(asset_dir)

        for file in asset_path.rglob("*"):
            if file.is_file():

                key = str(file.relative_to(asset_path))

                self.client.upload_file(
                    str(file),
                    self.bucket,
                    key,
                )

                uploaded.append(key)

        return uploaded

    # ------------------------------------------------
    # List
    # ------------------------------------------------

    def list_assets(self) -> List[str]:
        """
        List all objects in the bucket.
        """

        keys = []

        paginator = self.client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])

        return keys

    # ------------------------------------------------
    # Download
    # ------------------------------------------------

    def download_asset(self, key: str, output_path: str):
        """
        Download a file from S3 to disk.
        """

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        self.client.download_file(
            self.bucket,
            key,
            output_path,
        )

    # ------------------------------------------------
    # Stream
    # ------------------------------------------------

    def stream_asset(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """
        Stream a file from S3 without loading into memory.
        """

        obj = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )

        stream = obj["Body"]

        while True:
            chunk = stream.read(chunk_size)

            if not chunk:
                break

            yield chunk