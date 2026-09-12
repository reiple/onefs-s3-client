#!/usr/bin/env bash
# manylinux 컨테이너 *내부에서* 실행되는 빌드 스크립트.
#
# 호스트에서 직접 실행하지 말 것. 호출 예:
#   docker run --rm -v "$PWD":/io -w /io \
#     -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
#     quay.io/pypa/manylinux2014_x86_64 \
#     bash /io/packaging/build_linux_container.sh
#
# manylinux2014 = CentOS 7 기반(glibc 2.17). 여기서 빌드한 바이너리는
# RHEL/CentOS 7·8·9, Ubuntu 14.04 이상에서 그대로 동작한다.
set -euo pipefail

PYBIN="/opt/python/cp312-cp312/bin/python"
if [[ ! -x "$PYBIN" ]]; then
    echo "ERROR: Python 3.12 not found at $PYBIN" >&2
    echo "이미지에 포함된 Python 목록:" >&2
    ls -1 /opt/python >&2 || true
    exit 1
fi

echo "==> Python: $("$PYBIN" --version)"
echo "==> glibc : $(getconf GNU_LIBC_VERSION)"

export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1

# venv 는 /tmp 에 만든다. 마운트된 소스 트리를 root 소유 파일로 오염시키지 않기 위함.
VENV="/tmp/build-venv"
rm -rf "$VENV" build dist
"$PYBIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel
"$VENV/bin/python" -m pip install -r requirements.txt

echo "==> PyInstaller 빌드"
"$VENV/bin/python" -m PyInstaller --clean --noconfirm packaging/onefs-s3.spec

echo "==> 필요 glibc 버전 확인"
# 부트로더가 요구하는 최대 GLIBC 심볼 버전. 2.17 이하여야 CentOS 7 에서 실행된다.
if command -v objdump >/dev/null 2>&1; then
    objdump -T dist/onefs-s3 2>/dev/null \
        | grep -o 'GLIBC_[0-9.]*' \
        | sed 's/GLIBC_//' \
        | sort -uV \
        | tail -n 1 \
        | xargs -r -I{} echo "    required GLIBC <= {}"
fi

echo "==> 스모크 테스트"
./dist/onefs-s3 --help > /dev/null

# 마운트된 볼륨에 root 소유로 남은 산출물을 호스트 사용자에게 돌려준다.
if [[ -n "${HOST_UID:-}" && -n "${HOST_GID:-}" ]]; then
    chown -R "${HOST_UID}:${HOST_GID}" dist build 2>/dev/null || true
fi

echo "==> 완료: dist/onefs-s3"
