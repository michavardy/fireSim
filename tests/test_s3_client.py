import io
import importlib.util
import shutil
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.clients.s3_client import S3AssetClient


TREE_ASSET_ROOT = REPO_ROOT / "assets" / "tree_1"
ASSETS_MANAGER_PATH = REPO_ROOT / "scripts" / "assets_manager.py"

TREE_TEXTURE = TREE_ASSET_ROOT / "textures" / "tree_small_02_branch_diff_4k.png"
TEST_BUCKET = "test-tree-asset-bucket"


def _prepare_sample_assets(tmp_path: Path) -> Path:
    """Copy a small subset of the tree asset into a temp directory for uploading."""

    tree_asset_dir = tmp_path / "tree_asset"
    textures_target = tree_asset_dir / "textures"
    textures_target.mkdir(parents=True)

    shutil.copy(TREE_TEXTURE, textures_target / TREE_TEXTURE.name)
    (tree_asset_dir / "metadata.txt").write_text("tree asset metadata")

    return tree_asset_dir


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setenv("S3_API_KEY_NAME", TEST_BUCKET)
    monkeypatch.setenv("S3_API_KEY_ACCESS_KEY", "fake-access-key")
    monkeypatch.setenv("S3_API_KEY_SECRET_ACCESS_KEY", "fake-secret-key")

    return TEST_BUCKET


@pytest.fixture(scope="module")
def assets_manager_module():
    spec = importlib.util.spec_from_file_location(
        "assets_manager",
        ASSETS_MANAGER_PATH,
    )
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def s3_asset_client(s3_bucket):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_bucket)
        yield S3AssetClient()


def test_upload_all_assets_returns_relative_keys(s3_asset_client, tmp_path):
    asset_dir = _prepare_sample_assets(tmp_path)
    uploaded_keys = s3_asset_client.upload_all_assets(str(asset_dir))

    expected_keys = {
        "textures/tree_small_02_branch_diff_4k.png",
        "metadata.txt",
    }

    assert set(uploaded_keys) == expected_keys


def test_list_assets_returns_uploaded_keys(s3_asset_client, tmp_path):
    asset_dir = _prepare_sample_assets(tmp_path)
    uploaded_keys = set(s3_asset_client.upload_all_assets(str(asset_dir)))

    listed_keys = set(s3_asset_client.list_assets())

    assert listed_keys == uploaded_keys


def test_download_and_stream_asset_round_trip(s3_asset_client, tmp_path):
    asset_dir = _prepare_sample_assets(tmp_path)
    uploaded_keys = set(s3_asset_client.upload_all_assets(str(asset_dir)))

    png_key = next(key for key in uploaded_keys if key.endswith(".png"))
    download_path = tmp_path / "downloads" / Path(png_key)

    s3_asset_client.download_asset(png_key, str(download_path))

    original_bytes = TREE_TEXTURE.read_bytes()
    assert download_path.read_bytes() == original_bytes

    streamed_bytes = b"".join(s3_asset_client.stream_asset(png_key, chunk_size=4096))
    assert streamed_bytes == original_bytes


def test_assets_manager_cli_round_trip(
    s3_bucket, tmp_path, assets_manager_module
):
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=s3_bucket)
        asset_dir = _prepare_sample_assets(tmp_path)

        assert assets_manager_module.main(
            ["--load_dir", str(asset_dir)]
        ) == 0

        first_listing = io.StringIO()
        assert assets_manager_module.main(
            ["--list"],
            output_stream=first_listing,
        ) == 0

        assert "tree_small_02_branch_diff_4k.png" in first_listing.getvalue()
        assert "textures" in first_listing.getvalue()

        assert assets_manager_module.main(["--rm", "textures"]) == 0

        post_rm_listing = io.StringIO()
        assert assets_manager_module.main(
            ["--list"],
            output_stream=post_rm_listing,
        ) == 0

        assert "tree_small_02_branch_diff_4k.png" not in post_rm_listing.getvalue()

        s3_client = S3AssetClient()
        assert all(
            not key.startswith("textures/")
            for key in s3_client.list_assets()
        )

