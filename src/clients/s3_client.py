import os
from pathlib import Path
from typing import List, Iterator

import boto3
from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv


load_dotenv()


class S3AssetClient:
    """
    Lightweight asset client for streaming large files to and from S3.
    """

    def __init__(self):

        self.bucket = os.getenv("S3_BUCKET_NAME") or os.getenv("S3_API_KEY_NAME")
        access_key = os.getenv("S3_API_KEY_ACCESS_KEY")
        secret_key = os.getenv("S3_API_KEY_SECRET_ACCESS_KEY")

        if not all([self.bucket, access_key, secret_key]):
            raise RuntimeError("Missing S3 credentials in .env")

        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.transfer_config = TransferConfig(multipart_threshold=256 * 1024 * 1024)

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
                    Config=self.transfer_config,
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

    def delete_objects(self, keys: List[str]) -> List[str]:
        """
        Delete a collection of object keys from the bucket using batch delete.
        """

        if not keys:
            return []

        deleted = []

        for chunk_start in range(0, len(keys), 1000):
            chunk = keys[chunk_start : chunk_start + 1000]
            delete_response = self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": key} for key in chunk]},
            )
            deleted.extend(obj["Key"] for obj in delete_response.get("Deleted", []))

        return deleted

    def delete_prefix(self, prefix: str) -> List[str]:
        """
        Recursively delete every key that matches or begins with the given prefix.
        """

        normalized_prefix = prefix.strip("/")
        if not normalized_prefix:
            return []

        keys_to_delete = [
            key
            for key in self.list_assets()
            if key == normalized_prefix or key.startswith(f"{normalized_prefix}/")
        ]

        if not keys_to_delete:
            return []

        return self.delete_objects(keys_to_delete)


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