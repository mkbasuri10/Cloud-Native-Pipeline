from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import boto3
from botocore.exceptions import ClientError

from .config import Settings, settings as default_settings

_MOTO_CONTEXT = None


def start_moto() -> None:
    """Start moto's in-memory S3 mock for local development."""
    global _MOTO_CONTEXT
    if _MOTO_CONTEXT is None:
        # moto>=5 uses mock_aws; older versions don't accept services kwarg
        from moto import mock_aws

        _MOTO_CONTEXT = mock_aws()
        _MOTO_CONTEXT.start()


def stop_moto() -> None:
    """Stop moto's in-memory S3 mock."""
    global _MOTO_CONTEXT
    if _MOTO_CONTEXT is not None:
        _MOTO_CONTEXT.stop()
        _MOTO_CONTEXT = None


def get_s3_client(cfg: Settings | None = None):
    cfg = cfg or default_settings
    if cfg.s3_use_mock:
        start_moto()
    return boto3.client(
        "s3",
        region_name=cfg.s3_region,
        endpoint_url=cfg.s3_endpoint_url,
    )


class S3Storage:
    def __init__(self, bucket: str, prefix: str | None = None, cfg: Settings | None = None):
        self.cfg = cfg or default_settings
        self.client = get_s3_client(self.cfg)
        self.bucket = bucket
        self.prefix = (prefix or "").strip("/")

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            params = {"Bucket": self.bucket}
            if self.cfg.s3_region != "us-east-1":
                params["CreateBucketConfiguration"] = {"LocationConstraint": self.cfg.s3_region} # type: ignore
            self.client.create_bucket(**params)

    def key(self, name: str) -> str:
        if self.prefix:
            return f"{self.prefix}/{name}"
        return name

    def upload_file(self, local_path: Path, key: str) -> None:
        self.ensure_bucket()
        self.client.upload_file(str(local_path), self.bucket, key)

    def upload_text(self, text: str, key: str) -> None:
        self.ensure_bucket()
        self.client.put_object(Bucket=self.bucket, Key=key, Body=text.encode("utf-8"))

    def download_text(self, key: str) -> str:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read().decode("utf-8")

    def list_objects(self, prefix: str | None = None) -> list[str]:
        self.ensure_bucket()
        params = {"Bucket": self.bucket}
        if prefix:
            params["Prefix"] = prefix
        resp = self.client.list_objects_v2(**params)
        return [item["Key"] for item in resp.get("Contents", [])]

    def upload_directory(self, local_dir: Path, key_prefix: str) -> list[str]:
        uploaded = []
        for root, _, files in os.walk(local_dir):
            for name in files:
                path = Path(root) / name
                rel = path.relative_to(local_dir)
                key = f"{key_prefix}/{rel.as_posix()}"
                self.upload_file(path, key)
                uploaded.append(key)
        return uploaded

    def upload_jsonl(self, rows: Iterable[dict], key: str) -> None:
        payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        self.upload_text(payload, key)
