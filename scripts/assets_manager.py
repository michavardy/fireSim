"""Command line helper for managing assets in the configured S3 bucket."""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

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

    if args.bucket:
        os.environ["S3_BUCKET_NAME"] = args.bucket
        logger.info("Overriding bucket with %s", args.bucket)

    try:
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
