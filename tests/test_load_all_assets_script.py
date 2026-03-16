import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.load_all_assets import upload_assets_from_dir
from src.clients.s3_client import S3AssetClient


TREE_ASSET_ROOT = REPO_ROOT / "assets" / "tree_1"
TREE_TEXTURE = TREE_ASSET_ROOT / "textures" / "tree_small_02_branch_diff_4k.png"
TEST_BUCKET = "test-tree-asset-bucket"


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", TEST_BUCKET)
    monkeypatch.setenv("S3_API_KEY_ACCESS_KEY", "fake-access-key")
    monkeypatch.setenv("S3_API_KEY_SECRET_ACCESS_KEY", "fake-secret")

    return TEST_BUCKET


@pytest.fixture
def s3_asset_client(s3_bucket):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_bucket)
        yield S3AssetClient()


def test_script_uploads_tree_asset_and_streams(s3_asset_client):
    uploaded = upload_assets_from_dir(TREE_ASSET_ROOT, client=s3_asset_client)
    texture_key = "textures/tree_small_02_branch_diff_4k.png"

    assert texture_key in uploaded

    streamed_bytes = b"".join(s3_asset_client.stream_asset(texture_key, chunk_size=4096))
    assert streamed_bytes == TREE_TEXTURE.read_bytes()
