"""Utility to push local assets into S3 for reuse."""
import argparse
import logging
import os
from pathlib import Path
from typing import List, Optional

from src.clients.s3_client import S3AssetClient


logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload the assets/ directory to the configured S3 bucket.",
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=Path("assets"),
        help="Local directory containing the asset collection to upload.",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        help="Override the target bucket name for this run.",
    )
    return parser.parse_args()


def upload_assets_from_dir(
    asset_dir: Path, *, client: Optional[S3AssetClient] = None
) -> List[str]:
    """Upload every file under `asset_dir` using the provided S3 client."""

    asset_dir = Path(asset_dir)

    if not asset_dir.exists() or not asset_dir.is_dir():
        raise FileNotFoundError(f"Asset directory does not exist: {asset_dir}")

    s3_client = client or S3AssetClient()
    uploaded_keys = s3_client.upload_all_assets(str(asset_dir))

    for key in uploaded_keys:
        logger.info("Uploaded %s", key)

    logger.info(
        "Finished uploading assets from %s (%d files) to %s",
        asset_dir,
        len(uploaded_keys),
        s3_client.bucket,
    )

    return uploaded_keys


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    )


def main() -> int:
    args = parse_args()
    configure_logging()

    if args.bucket:
        os.environ["S3_BUCKET_NAME"] = args.bucket
        logger.info("Using overridden bucket %s", args.bucket)

    try:
        upload_assets_from_dir(args.asset_dir)
    except Exception as exc:
        logger.exception("Failed to upload assets: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
