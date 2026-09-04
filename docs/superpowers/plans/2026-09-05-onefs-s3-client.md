# OneFS S3 Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a maintainable OneFS S3 CLI that can be built into a standalone Windows EXE.

**Architecture:** Use small Python modules: config loading, safe logger setup, boto3 S3 operations, and CLI dispatch. Keep tests focused on deterministic behavior that does not require a real OneFS endpoint.

**Tech Stack:** Python 3.11, boto3, botocore, PyInstaller, unittest.

**Spec:** `docs/superpowers/specs/2026-09-05-onefs-s3-client-design.md`

## Global Constraints

- Python 3.11 기준
- boto3 사용
- botocore 사용
- Windows 10 / Windows 11 / Windows Server 2019 / Windows Server 2022에서 실행 가능
- 최종 배포 파일은 PyInstaller EXE
- Secret Key, Authorization header, AWS Signature 로그 출력 금지
- `config.json`은 Git 제외, `config.json.example`만 포함

---

### Task 1: Deterministic Core Utilities

**Files:**
- Create: `tests/test_config.py`
- Create: `tests/test_formatting_and_errors.py`
- Create: `src/config.py`
- Create: `src/s3_client.py`
- Create: `src/logger.py`

**Interfaces:**
- Produces: `AppConfig`, `load_config(path: Path | None) -> AppConfig`, `mask_secret(value: str) -> str`, `human_size(size: int) -> str`, `describe_error(exc: BaseException, endpoint: str) -> str`

- [x] Write failing tests for config loading, masking, size formatting, and error mapping.
- [x] Run tests and confirm they fail because implementation is missing.
- [x] Implement minimal core modules.
- [x] Run tests and confirm they pass.

### Task 2: CLI And S3 Operations

**Files:**
- Create: `src/main.py`
- Modify: `src/s3_client.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `AppConfig`, `OneFSS3Client`
- Produces: CLI commands `test`, `buckets`, `list`, `download`, `info`, `upload`

- [x] Add command dispatch around the core modules.
- [x] Implement boto3-backed operations and diagnostic checks.
- [x] Add README usage and manual test scenarios.
- [x] Run import/CLI help/unit verification.

### Task 3: Packaging Files

**Files:**
- Create: `requirements.txt`
- Create: `build.bat`
- Create: `config.json.example`
- Create: `.gitignore`
- Create: `src/__init__.py`

**Interfaces:**
- Produces: Windows build command yielding `dist\onefs-s3.exe`

- [x] Add packaging and example config files.
- [x] Verify syntax and test suite.
