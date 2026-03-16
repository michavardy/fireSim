"""Command line helper for managing assets in the configured S3 bucket."""
import argparse
import logging
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

import boto3
from botocore.exceptions import ClientError as BotoClientError

try:
    from moto import mock_aws
except ImportError:  # pragma: no cover - optional dependency
    mock_aws = None

from src.clients.s3_client import S3AssetClient


logger = logging.getLogger(__name__)
DEFAULT_ASSET_DIR = Path("assets")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage local assets in the configured S3 bucket.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--load_all",
        action="store_true",
        help="Upload every file from the default assets/ directory.",
    )
    group.add_argument(
        "--load_dir",
        type=Path,
        metavar="DIR",
        help="Upload all files from a specific local directory.",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="Print a recursive tree of objects currently stored in S3.",
    )
    group.add_argument(
        "--rm",
        dest="rm_prefix",
        metavar="NAME",
        help="Recursively delete objects/prefixes that match the provided name.",
    )

    parser.add_argument(
        "--bucket",
        type=str,
        help="Override the target bucket name for this run.",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run against a moto mock AWS S3 service for local testing.",
    )

    return parser.parse_args(argv)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    )


def upload_assets_from_dir(
    asset_dir: Path, *, client: Optional[S3AssetClient] = None
) -> List[str]:
    asset_dir = Path(asset_dir)

    if not asset_dir.exists() or not asset_dir.is_dir():
        raise FileNotFoundError(f"Asset directory does not exist: {asset_dir}")

    s3_client = client or S3AssetClient()
    uploaded_keys = s3_client.upload_all_assets(str(asset_dir))

    for key in uploaded_keys:
        logger.info("Uploaded %s", key)

    logger.info(
        "Finished uploading %s assets to %s",
        asset_dir,
        s3_client.bucket,
    )

    return uploaded_keys


def _prepare_mock_environment(bucket_override: Optional[str]) -> str:
    """Prepare the moto mock S3 environment so commands can run offline."""

    if mock_aws is None:
        raise RuntimeError("moto is required for --mock mode")

    bucket = (
        bucket_override
        or os.getenv("S3_BUCKET_NAME")
        or os.getenv("S3_API_KEY_NAME")
        or "fire-sim-assets-local"
    )

    os.environ.setdefault("S3_BUCKET_NAME", bucket)
    os.environ.setdefault("S3_API_KEY_NAME", bucket)
    os.environ.setdefault("S3_API_KEY_ACCESS_KEY", "mock-access-key")
    os.environ.setdefault("S3_API_KEY_SECRET_ACCESS_KEY", "mock-secret-key")

    client = boto3.client("s3", region_name="us-east-1")
    try:
        client.create_bucket(Bucket=bucket)
    except BotoClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise

    logger.info("Using moto mock S3 bucket %s", bucket)
    return bucket


def _build_prefix_tree(keys: List[str]) -> Dict[str, Any]:
    tree: Dict[str, Any] = {}

    for key in sorted(keys):
        node = tree
        for part in key.split("/"):
            node = node.setdefault(part, {})

    return tree


def _format_tree(tree: Dict[str, Any], prefix: str = "") -> List[str]:
    lines: List[str] = []
    entries = sorted(tree.items())

    for index, (name, subtree) in enumerate(entries):
        connector = "└── " if index == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{name}")

        if subtree:
            extension = "    " if index == len(entries) - 1 else "│   "
            lines.extend(_format_tree(subtree, prefix + extension))

    return lines


def list_bucket_tree(
    client: S3AssetClient, *, output_stream: TextIO = sys.stdout
) -> List[str]:
    keys = client.list_assets()

    if not keys:
        print("(empty bucket)", file=output_stream)
        return keys

    tree = _build_prefix_tree(keys)
    for line in _format_tree(tree):
        print(line, file=output_stream)

    return keys


def remove_prefix(name: str, *, client: Optional[S3AssetClient] = None) -> List[str]:
    s3_client = client or S3AssetClient()
    deleted = s3_client.delete_prefix(name)

    if not deleted:
        logger.warning("No objects matched %s", name)
        return []

    for key in deleted:
        logger.info("Deleted %s", key)

    return deleted


def main(argv: Optional[List[str]] = None, *, output_stream: TextIO = sys.stdout) -> int:
    args = parse_args(argv)
    configure_logging()

    if args.mock and mock_aws is None:
        logger.error(
            "moto is required for --mock mode. Install it with `pip install moto`."
        )
        return 1

    mock_context = mock_aws() if args.mock else nullcontext()

    try:
        with mock_context:
            if args.bucket:
                os.environ["S3_BUCKET_NAME"] = args.bucket
                logger.info("Overriding bucket with %s", args.bucket)

            if args.mock:
                _prepare_mock_environment(args.bucket)

            client = S3AssetClient()

            if args.load_all:
                upload_assets_from_dir(DEFAULT_ASSET_DIR, client=client)
            elif args.load_dir:
                upload_assets_from_dir(args.load_dir, client=client)
            elif args.list:
                list_bucket_tree(client, output_stream=output_stream)
            elif args.rm_prefix:
                remove_prefix(args.rm_prefix, client=client)
            else:
                logger.error("No operation selected")
                return 1
    except Exception as exc:
        logger.exception("Assets manager failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
