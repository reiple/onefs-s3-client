# -*- mode: python ; coding: utf-8 -*-
"""Windows / Linux 공용 PyInstaller spec.

CLI 플래그 대신 spec 을 쓰는 이유:
  - 로컬 빌드(build.bat / build.sh)와 GitHub Actions 가 완전히 동일한 설정을 쓴다.
  - exclude / hiddenimports 를 한 곳에서만 관리한다.

빌드:  pyinstaller --clean --noconfirm packaging/onefs-s3.spec
결과:  dist/onefs-s3(.exe)
"""

import sys
from pathlib import Path

# SPECPATH 는 PyInstaller 가 주입하는 전역 변수(= 이 spec 파일이 있는 디렉터리)
ROOT = Path(SPECPATH).resolve().parent  # noqa: F821

IS_WINDOWS = sys.platform.startswith("win")

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    # boto3/botocore 의 데이터 파일(endpoints.json, service-2.json)은
    # pyinstaller-hooks-contrib 의 기본 훅이 자동으로 수집한다.
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # botocore 는 S3 XML 응답 파싱에 xml.etree 를 쓰므로 xml 은 절대 제외하지 말 것.
    excludes=[
        "tkinter",
        "test",
        "lib2to3",
        "pydoc_data",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="onefs-s3",
    debug=False,
    bootloader_ignore_signals=False,
    # Linux 에서만 strip: 바이너리 크기를 줄인다.
    # Windows 는 strip 이 PE 를 손상시킬 수 있어 끈다.
    strip=not IS_WINDOWS,
    # UPX 압축은 백신 오탐(false positive)의 주요 원인이라 사용하지 않는다.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
