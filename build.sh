#!/usr/bin/env bash
# Linux 로컬 빌드(네이티브). 현재 머신의 glibc 에 링크되므로
# 빌드 머신보다 오래된 배포판에서는 동작하지 않을 수 있다.
#
# 배포용 바이너리는 glibc 2.17 컨테이너에서 빌드해야 한다:
#   docker run --rm -v "$PWD":/io -w /io \
#     -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
#     quay.io/pypa/manylinux2014_x86_64 /io/packaging/build_linux_container.sh
set -euo pipefail

PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m PyInstaller --clean --noconfirm packaging/onefs-s3.spec

cp config.json.example dist/config.json.example
echo "Build completed: dist/onefs-s3"
