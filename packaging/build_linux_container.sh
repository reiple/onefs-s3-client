#!/usr/bin/env bash
# 빌드 컨테이너 *내부에서* 실행되는 스크립트.
#
# 호스트에서 직접 실행하지 말 것. 호출 예:
#   docker run --rm -v "$PWD":/io -w /io \
#     -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
#     quay.io/pypa/manylinux2014_x86_64 \
#     bash /io/packaging/build_linux_container.sh
#
# ── 왜 이런 구조인가 ────────────────────────────────────────────────────────
#
# PyInstaller 는 부트로더와 C 확장 모듈을 빌드 머신의 glibc 에 동적 링크한다.
# glibc 는 하위 호환만 되므로 가장 오래된 지원 대상(CentOS 7 = glibc 2.17)에서
# 빌드해야 한다. 그래서 컨테이너는 glibc 2.17 인 manylinux2014(CentOS 7 기반)를
# 쓰고, binutils(strip/objdump)도 여기 들어 있다.
#
# 단, 그 이미지에 들어 있는 /opt/python 의 CPython 은 쓸 수 없다. 휠 빌드 전용이라
# --enable-shared 없이 빌드되어 libpython3.12.so 가 없고, PyInstaller 가
#   ERROR: Python was built without a shared library
# 로 실패한다. CentOS 7 은 Python 3.12 패키지도 제공하지 않는다(OpenSSL 도 1.0.2).
#
# 따라서 인터프리터는 python-build-standalone 의 재배치 가능 CPython 을 쓴다.
#   - Py_ENABLE_SHARED=1  (libpython3.12.so.1.0 포함)  -> PyInstaller 사용 가능
#   - 요구 glibc 심볼 상한 2.17                        -> CentOS 7 에서 동작
#   - OpenSSL 3.5.8 이 libpython 에 정적 링크           -> 시스템 OpenSSL 불필요
set -euo pipefail

# python-build-standalone 배포판 고정.
# 갱신 시 https://github.com/astral-sh/python-build-standalone/releases 의
# SHA256SUMS 에서 체크섬을 함께 갱신할 것.
PBS_RELEASE="20260901"
PBS_PYTHON="3.12.14"
PBS_ARCHIVE="cpython-${PBS_PYTHON}+${PBS_RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${PBS_ARCHIVE}"
PBS_SHA256="936c246dfdbbfa7cb22dd01814a21f582a892689fae96b06071a5e433baffa22"

echo "==> 빌드 호스트 glibc: $(getconf GNU_LIBC_VERSION)"

echo "==> CPython ${PBS_PYTHON} 내려받기 (python-build-standalone ${PBS_RELEASE})"
curl -fsSL --retry 3 -o /tmp/python.tar.gz "$PBS_URL"

echo "==> 체크섬 검증"
echo "${PBS_SHA256}  /tmp/python.tar.gz" | sha256sum -c -

rm -rf /opt/pbs
mkdir -p /opt/pbs
tar -xzf /tmp/python.tar.gz -C /opt/pbs   # -> /opt/pbs/python
PYBIN="/opt/pbs/python/bin/python3.12"

echo "==> Python: $("$PYBIN" --version)"

# Py_ENABLE_SHARED 가 0 이면 PyInstaller 가 동작하지 않는다. 빌드 전에 확인한다.
shared="$("$PYBIN" -c 'import sysconfig; print(sysconfig.get_config_var("Py_ENABLE_SHARED"))')"
echo "==> Py_ENABLE_SHARED: ${shared}"
if [[ "$shared" != "1" ]]; then
    echo "ERROR: 공유 라이브러리로 빌드된 Python 이 아닙니다. PyInstaller 를 쓸 수 없습니다." >&2
    exit 1
fi
echo "==> OpenSSL: $("$PYBIN" -c 'import ssl; print(ssl.OPENSSL_VERSION)')"

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

# 부트로더가 요구하는 최대 GLIBC 심볼 버전을 확인한다.
# 번들 안에 압축된 libpython 등은 여기서 보이지 않으므로 이 검사는 1차 방어선이다.
# 최종 확인은 워크플로우의 verify-linux 잡이 centos:7 컨테이너에서 실제로 실행해 수행한다.
MAX_GLIBC="2.17"
echo "==> 필요 glibc 버전 확인 (허용 상한 ${MAX_GLIBC})"
required="$(objdump -T dist/onefs-s3 2>/dev/null \
    | grep -o 'GLIBC_[0-9.]*' | sed 's/GLIBC_//' | sort -uV | tail -n 1)"
echo "    requires GLIBC <= ${required:-unknown}"
if [[ -n "$required" ]] \
   && [[ "$(printf '%s\n%s\n' "$MAX_GLIBC" "$required" | sort -V | tail -n 1)" != "$MAX_GLIBC" ]]; then
    echo "ERROR: glibc ${required} 를 요구합니다. CentOS 7(${MAX_GLIBC}) 에서 실행할 수 없습니다." >&2
    exit 1
fi

echo "==> 스모크 테스트"
./dist/onefs-s3 --help > /dev/null

# 마운트된 볼륨에 root 소유로 남은 산출물을 호스트 사용자에게 돌려준다.
if [[ -n "${HOST_UID:-}" && -n "${HOST_GID:-}" ]]; then
    chown -R "${HOST_UID}:${HOST_GID}" dist build 2>/dev/null || true
fi

echo "==> 완료: dist/onefs-s3"
