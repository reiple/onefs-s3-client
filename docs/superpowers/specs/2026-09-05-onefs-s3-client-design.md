# OneFS S3 Client Design

**Goal:** Build a Windows-friendly Python CLI for Dell PowerScale OneFS S3 that can be packaged as a standalone executable.

**Architecture:** The CLI is split into configuration loading, logging setup, S3 operations, and command dispatch. `src/main.py` owns argparse and user-facing flow, `src/config.py` owns config file discovery and validation, `src/logger.py` owns safe logging, and `src/s3_client.py` owns boto3/botocore integration and error translation.

**Runtime:** Python 3.11, boto3, botocore, PyInstaller. The executable reads `config.json` from the executable directory when frozen and from the project root during source execution unless `--config` is provided.

**Security:** Secrets are never hardcoded. Secret keys, Authorization headers, and AWS signatures are filtered out of logs. Access keys are masked when logged. `verify_ssl=false` prints a warning.

**CLI Commands:** `test`, `buckets`, `list`, `download`, `info`, and `upload` are implemented. Listings use `list_objects_v2` paginator and show key, human-readable size, and local timestamp. Downloads create destination directories and use boto3 transfer APIs.

**Diagnostics:** The `test` command checks config, endpoint syntax, DNS, TCP, SSL, S3 auth, and bucket access in order. Error handling translates DNS, timeout, connection refused, SSL, access, missing bucket/key, signature, clock skew, endpoint, read timeout, and generic client errors into Korean user-facing messages.

**Testing:** Unit tests cover config defaults/validation, byte-size formatting, error translation, and log masking without requiring a real OneFS server.
