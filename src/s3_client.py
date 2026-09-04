from __future__ import annotations

import logging
import socket
import ssl
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from src.config import AppConfig


class DiagnosticFailure(RuntimeError):
    pass


def human_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B" or value.is_integer():
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"


def describe_error(exc: BaseException, endpoint: str) -> str:
    text = str(exc)
    lower = text.lower()
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error", {})
        code = str(error.get("Code", "ClientError"))
        return _describe_s3_error(code, endpoint, response)

    class_name = exc.__class__.__name__
    if isinstance(exc, socket.gaierror) or "name or service not known" in lower:
        return (
            "[ERROR] DNS Resolution 실패\n"
            f"Endpoint: {endpoint}\n\n"
            "가능한 원인:\n- DNS 설정\n- Endpoint URL"
        )
    if isinstance(exc, TimeoutError) or "timeout" in lower or class_name == "ReadTimeoutError":
        return (
            "[ERROR] Connection timeout\n"
            f"Endpoint: {endpoint}\n\n"
            "가능한 원인:\n- 네트워크 지연\n- 방화벽\n- OneFS S3 서비스 응답 지연"
        )
    if isinstance(exc, ConnectionRefusedError) or "connection refused" in lower:
        return (
            "[ERROR] Connection refused\n"
            f"Endpoint: {endpoint}\n\n"
            "가능한 원인:\n- 포트 차단\n- OneFS S3 서비스 중지"
        )
    if "ssl" in lower or "certificate" in lower or class_name == "SSLError":
        return (
            "[ERROR] SSL 인증서 오류\n"
            f"Endpoint: {endpoint}\n\n"
            "가능한 원인:\n- 자체 서명 인증서\n- 사설 CA 미설정\n- 인증서 만료 또는 hostname 불일치"
        )
    if class_name.endswith("EndpointConnectionError") or "could not connect to the endpoint" in lower:
        return (
            "[ERROR] OneFS S3 서버에 연결할 수 없습니다.\n"
            f"Endpoint: {endpoint}\n\n"
            "가능한 원인:\n- DNS 설정\n- 방화벽\n- Endpoint URL\n- OneFS S3 서비스 상태"
        )
    return f"[ERROR] {class_name}\nEndpoint: {endpoint}\n{text}"


def _describe_s3_error(code: str, endpoint: str, response: dict[str, Any]) -> str:
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    messages = {
        "Unauthorized": "인증 정보가 올바르지 않습니다.",
        "AccessDenied": "접근 권한이 없습니다.",
        "NoSuchKey": "Object를 찾을 수 없습니다.",
        "404": "Object를 찾을 수 없습니다.",
        "NoSuchBucket": "Bucket을 찾을 수 없습니다.",
        "SignatureDoesNotMatch": "Secret Key 또는 서명 설정이 올바르지 않습니다.",
        "RequestTimeTooSkewed": "클라이언트와 OneFS 서버의 시간이 크게 차이납니다.",
    }
    if status == 401:
        code = "401 Unauthorized"
    if status == 403 and code == "ClientError":
        code = "403 AccessDenied"
    detail = messages.get(code, messages.get(code.replace("403 ", ""), "S3 API 호출 중 오류가 발생했습니다."))
    return f"[ERROR] {code}\nEndpoint: {endpoint}\n{detail}"


class OneFSS3Client:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.client = self._build_client()

    def _build_client(self) -> Any:
        import boto3
        from botocore.config import Config

        boto_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": self.config.s3_addressing_style},
            retries={"max_attempts": 3, "mode": "standard"},
        )
        return boto3.client(
            "s3",
            endpoint_url=self.config.endpoint_url,
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region_name,
            verify=self.config.verify_parameter,
            config=boto_config,
        )

    def list_buckets(self) -> list[str]:
        response = self.client.list_buckets()
        buckets = [bucket["Name"] for bucket in response.get("Buckets", [])]
        self.logger.info("Listed %s buckets", len(buckets))
        return buckets

    def list_objects(self, prefix: str = "") -> Iterable[dict[str, Any]]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix):
            for item in page.get("Contents", []):
                yield item

    def download(self, key: str, output: Path | None = None) -> Path:
        destination = output or Path(key).name
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(f"{destination.name}.part")
        try:
            self.client.download_file(self.config.bucket_name, key, str(partial))
            partial.replace(destination)
        except Exception:
            if partial.exists():
                partial.unlink()
            raise
        self.logger.info("Downloaded object key=%s output=%s", key, destination)
        return destination

    def upload(self, source: Path, key: str) -> None:
        if not source.exists():
            raise FileNotFoundError(f"Upload source file not found: {source}")
        self.client.upload_file(str(source), self.config.bucket_name, key)
        self.logger.info("Uploaded file source=%s key=%s", source, key)

    def object_info(self, key: str) -> dict[str, Any]:
        response = self.client.head_object(Bucket=self.config.bucket_name, Key=key)
        self.logger.info("Read object metadata key=%s", key)
        return response

    def assert_bucket_access(self) -> None:
        self.client.head_bucket(Bucket=self.config.bucket_name)


def endpoint_host_port(endpoint_url: str) -> tuple[str, int]:
    parsed = urlparse(endpoint_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid endpoint URL: {endpoint_url}")
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.hostname, parsed.port or default_port


def check_endpoint_url(endpoint_url: str) -> None:
    endpoint_host_port(endpoint_url)


def check_dns(endpoint_url: str) -> list[tuple[Any, ...]]:
    host, port = endpoint_host_port(endpoint_url)
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def check_tcp(endpoint_url: str, timeout: float = 5.0) -> None:
    host, port = endpoint_host_port(endpoint_url)
    with socket.create_connection((host, port), timeout=timeout):
        return


def check_ssl(endpoint_url: str, verify: bool | str, timeout: float = 5.0) -> None:
    parsed = urlparse(endpoint_url)
    if parsed.scheme != "https":
        return
    host, port = endpoint_host_port(endpoint_url)
    context = ssl.create_default_context(cafile=str(verify) if isinstance(verify, str) else None)
    if verify is False:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=host):
            return


def response_time_skew_seconds(response: dict[str, Any]) -> float | None:
    headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})
    date_header = headers.get("date")
    if not date_header:
        return None
    server_time = parsedate_to_datetime(date_header)
    if server_time.tzinfo is None:
        return None
    return abs((datetime.now(server_time.tzinfo) - server_time).total_seconds())
