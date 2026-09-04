from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import application_base_dir, load_config, safe_config_for_log
from src.logger import setup_logger
from src.s3_client import (
    OneFSS3Client,
    check_dns,
    check_endpoint_url,
    check_ssl,
    check_tcp,
    describe_error,
    human_size,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="onefs-s3", description="Dell PowerScale OneFS S3 client")
    parser.add_argument("--config", type=Path, help="Path to config.json")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("test", help="Run connection diagnostics")
    subparsers.add_parser("buckets", help="List accessible buckets")

    list_parser = subparsers.add_parser("list", help="List objects in configured bucket")
    list_parser.add_argument("--prefix", default="", help="Object key prefix")

    download_parser = subparsers.add_parser("download", help="Download an object")
    download_parser.add_argument("key")
    download_parser.add_argument("--output", type=Path)

    info_parser = subparsers.add_parser("info", help="Show object metadata")
    info_parser.add_argument("key")

    upload_parser = subparsers.add_parser("upload", help="Upload a file")
    upload_parser.add_argument("source", type=Path)
    upload_parser.add_argument("--key", required=True)

    return parser


def print_object_row(item: dict[str, Any]) -> None:
    last_modified = item.get("LastModified")
    if hasattr(last_modified, "strftime"):
        last_modified_text = last_modified.strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_modified_text = str(last_modified or "")
    print(f"{item.get('Key', '')}\t{human_size(int(item.get('Size', 0)))}\t{last_modified_text}")


def run_test(client: OneFSS3Client, logger: logging.Logger) -> int:
    config = client.config
    print("OneFS S3 Connection Test\n")
    print(f"Endpoint : {config.endpoint_url}")
    print(f"Bucket   : {config.bucket_name}\n")

    checks = [
        ("Configuration", lambda: None),
        ("Endpoint URL", lambda: check_endpoint_url(config.endpoint_url)),
        ("DNS Resolution", lambda: check_dns(config.endpoint_url)),
        ("TCP Connection", lambda: check_tcp(config.endpoint_url)),
        ("SSL Connection", lambda: check_ssl(config.endpoint_url, config.verify_parameter)),
        ("S3 Authentication", lambda: client.list_buckets()),
        ("Bucket Access", lambda: client.assert_bucket_access()),
    ]

    for name, check in checks:
        try:
            check()
        except Exception as exc:
            logger.exception("Connection test failed at %s", name)
            print(f"[FAIL] {name}")
            print()
            print(describe_error(exc, config.endpoint_url))
            return 1
        print(f"[OK] {name}")

    print("\nConnection test completed successfully.")
    return 0


def run_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    logger = setup_logger(application_base_dir())
    logger.info("Command=%s config=%s", args.command, safe_config_for_log(config))

    if not config.verify_ssl:
        print("[WARNING] SSL certificate verification is disabled.")
        print("This configuration should only be used in a trusted network.")

    client = OneFSS3Client(config, logger)

    if args.command == "test":
        return run_test(client, logger)
    if args.command == "buckets":
        for bucket in client.list_buckets():
            print(bucket)
        return 0
    if args.command == "list":
        for item in client.list_objects(args.prefix):
            print_object_row(item)
        return 0
    if args.command == "download":
        destination = client.download(args.key, args.output)
        print(f"Downloaded: {destination}")
        return 0
    if args.command == "info":
        info = client.object_info(args.key)
        for key in ["ContentLength", "ContentType", "LastModified", "ETag", "Metadata"]:
            if key in info:
                print(f"{key}: {info[key]}")
        return 0
    if args.command == "upload":
        client.upload(args.source, args.key)
        print(f"Uploaded: {args.source} -> {args.key}")
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_command(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        try:
            config = load_config(args.config)
            endpoint = config.endpoint_url
        except Exception:
            endpoint = "unknown"
        print(describe_error(exc, endpoint))
        return 1


if __name__ == "__main__":
    sys.exit(main())
