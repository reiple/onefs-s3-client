#!/usr/bin/env bash
# 빌드 컨테이너 *내부에서* 실행되는 스크립트.
#
# 호스트에서 직접 실행하지 말 것. 호출 예:
#   docker run --rm -v "$PWD":/io -w /io \
#     -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
#     almalinux:8 bash /io/packaging/build_linux_container.sh
#
# 왜 AlmaLinux 8 인가:
#   PyInstaller 는 부트로더와 C 확장 모듈을 빌드 머신의 glibc 에 동적 링크한다.
#   glibc 는 하위 호환만 되므로 가장 오래된 지원 대상에서 빌드해야 한다.
#   AlmaLinux 8 = glibc 2.28 = RHEL 8 과 바이너리 호환이고,
#   여기서 만든 바이너리는 RHEL/CentOS 8·9 와 Ubuntu 20.04 이상에서 동작한다.
#
# 왜 manylinux 이미지를 쓰지 않는가:
#   quay.io/pypa/manylinux* 의 CPython 은 휠 빌드 전용이라 --enable-shared 없이
#   정적으로 빌드되어 있다. PyInstaller 는 인터프리터를 번들에 심기 위해
#   libpython3.12.so 를 요구하므로 다음 오류로 실패한다:
#     ERROR: Python was built without a shared library, which is required by PyInstaller.
#   RHEL AppStream 의 python3.12 는 공유 라이브러리 빌드라 이 문제가 없다.
set -euo pipefail

echo "==> 빌드 의존성 설치"
# python3.12      : 인터프리터 + libpython3.12.so (python3.12-libs)
# python3.12-pip  : venv 부트스트랩
# binutils        : spec 의 strip=True 및 glibc 심볼 확인용 objdump
dnf -y install python3.12 python3.12-pip binutils

PYBIN="$(command -v python3.12 || true)"
if [[ -z "$PYBIN" ]]; then
    echo "ERROR: python3.12 를 찾을 수 없습니다." >&2
    exit 1
fi

echo "==> Python: $("$PYBIN" --version)"
echo "==> glibc : $(getconf GNU_LIBC_VERSION)"
# Py_ENABLE_SHARED 가 0 이면 PyInstaller 가 동작하지 않는다. 빌드 전에 확인한다.
shared="$("$PYBIN" -c 'import sysconfig; print(sysconfig.get_config_var("Py_ENABLE_SHARED"))')"
echo "==> Py_ENABLE_SHARED: ${shared}"
if [[ "$shared" != "1" ]]; then
    echo "ERROR: 공유 라이브러리로 빌드된 Python 이 아닙니다. PyInstaller 를 쓸 수 없습니다." >&2
    exit 1
fi

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
# 부트로더가 요구하는 최대 GLIBC 심볼 버전.
if command -v objdump >/dev/null 2>&1; then
    objdump -T dist/onefs-s3 2>/dev/null \
        | grep -o 'GLIBC_[0-9.]*' \
        | sed 's/GLIBC_//' \
        | sort -uV \
        | tail -n 1 \
        | xargs -r -I{} echo "    bootloader requires GLIBC <= {}"
fi

echo "==> 스모크 테스트"
./dist/onefs-s3 --help > /dev/null

# 마운트된 볼륨에 root 소유로 남은 산출물을 호스트 사용자에게 돌려준다.
if [[ -n "${HOST_UID:-}" && -n "${HOST_GID:-}" ]]; then
    chown -R "${HOST_UID}:${HOST_GID}" dist build 2>/dev/null || true
fi

echo "==> 완료: dist/onefs-s3"
