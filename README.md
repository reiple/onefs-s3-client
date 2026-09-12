# OneFS S3 Client

Windows에서 Dell PowerScale OneFS S3(Object Storage)에 접속해 bucket/object를 조회하고 파일을 업로드/다운로드하는 CLI입니다.

## 개발 환경 준비

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 설정

`config.json.example`을 `config.json`으로 복사한 뒤 환경에 맞게 수정합니다.

```json
{
  "endpoint_url": "https://onefs-s3.example.com",
  "access_key": "ACCESS_KEY",
  "secret_key": "SECRET_KEY",
  "region_name": "us-east-1",
  "bucket_name": "my-bucket",
  "verify_ssl": true,
  "ca_bundle": "",
  "s3_addressing_style": "path"
}
```

자체 서명 인증서를 임시로 허용해야 하면 다음처럼 설정할 수 있습니다.

```json
"verify_ssl": false
```

사설 CA를 사용하는 경우:

```json
"verify_ssl": true,
"ca_bundle": "certs/company-ca.pem"
```

## 실행

```cmd
python src\main.py test
python src\main.py buckets
python src\main.py list
python src\main.py list --prefix folder1/
python src\main.py download test/data.csv
python src\main.py download test/data.csv --output C:\temp\data.csv
python src\main.py info test/data.csv
python src\main.py upload C:\temp\data.csv --key test/data.csv
```

별도 설정 파일을 지정할 수 있습니다.

```cmd
python src\main.py --config C:\config\onefs.json test
```

## 빌드

빌드 결과물은 PyInstaller onefile 실행 파일이며 **대상 서버에 Python 설치가 필요하지 않습니다.**
Windows/Linux 모두 `packaging/onefs-s3.spec` 하나를 공유하므로 로컬 빌드와 CI 빌드 설정이 같습니다.

### GitHub Actions (권장)

`.github/workflows/build.yml` 이 Python 3.12 기준으로 Windows/Linux 바이너리를 만들고,
실제 배포 대상 배포판에서 실행까지 검증합니다.

| 트리거 | 동작 |
| --- | --- |
| `main` push / PR | 테스트 → 빌드 → 배포판 실행 검증 → artifact 업로드 |
| `v*` 태그 push | 위 과정 + GitHub Release 생성 |
| 수동 실행 | Actions 탭의 `Build & Release` → Run workflow |

릴리스 생성 예시:

```bash
git tag v1.0.0
git push origin v1.0.0
```

산출물:

```text
onefs-s3-<version>-windows-x64.zip        (+ .sha256)
onefs-s3-<version>-linux-x86_64.tar.gz    (+ .sha256)
```

### Linux 바이너리의 호환 범위

PyInstaller 는 Python 인터프리터는 번들에 넣지만 부트로더와 C 확장 모듈은
**빌드 머신의 glibc 에 동적 링크**합니다. glibc 는 하위 호환만 되므로,
최신 Ubuntu 에서 빌드한 바이너리는 RHEL 8 에서 `GLIBC_2.34 not found` 로 실행되지 않습니다.

그래서 Linux 빌드는 glibc 2.17(CentOS 7) 기반의 `quay.io/pypa/manylinux2014_x86_64`
컨테이너 안에서 수행합니다. 결과 바이너리는 다음 환경에서 실행 검증됩니다.

| 배포판 | glibc |
| --- | --- |
| CentOS 7 | 2.17 |
| RHEL 8 / CentOS 8 (AlmaLinux 8) | 2.28 |
| RHEL 9 (AlmaLinux 9) | 2.34 |
| Ubuntu 20.04 / 22.04 / 24.04 | 2.31 / 2.35 / 2.39 |

RHEL 8 이상만 지원하면 되는 경우 워크플로우의 `MANYLINUX_IMAGE` 를
`quay.io/pypa/manylinux_2_28_x86_64` 로 바꾸면 빌드가 빨라집니다.

### 로컬 빌드

Windows:

```cmd
build.bat
```

Linux (배포용, glibc 2.17 컨테이너 사용 — CI 와 동일한 산출물):

```bash
docker run --rm \
  -v "$PWD":/io -w /io \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  quay.io/pypa/manylinux2014_x86_64 \
  bash /io/packaging/build_linux_container.sh
```

Linux (개발용, 현재 머신의 Python 3.12 사용):

```bash
./build.sh
```

결과:

```text
dist\onefs-s3.exe   (Windows)
dist/onefs-s3       (Linux)
```

## 배포

### Windows

```text
onefs-s3.exe
config.json
```

### Linux

```bash
tar -xzf onefs-s3-<version>-linux-x86_64.tar.gz
cd onefs-s3-<version>-linux-x86_64
cp config.json.example config.json     # 값을 환경에 맞게 수정
chmod +x onefs-s3
./onefs-s3 test
```

사설 CA 인증서가 필요하면 함께 전달합니다.

```text
certs/company-ca.pem
```

`config.json` 과 `logs/` 는 실행 파일이 있는 디렉터리를 기준으로 찾습니다.
`/usr/local/bin` 처럼 쓰기 권한이 없는 위치에 두려면 `--config` 로 경로를 지정하고,
쓰기 가능한 작업 디렉터리에서 실행하세요.

배포 대상 서버에는 Python 설치가 필요하지 않습니다.

### 배포 시 참고

- onefile 실행 파일은 기동할 때마다 자기 자신을 임시 디렉터리에 풀어 놓습니다.
  `/tmp` 가 `noexec` 로 마운트된 서버에서는 `TMPDIR=/var/tmp/onefs-s3 ./onefs-s3 test`
  처럼 실행 가능한 경로를 지정하세요.
- 한글 메시지가 깨지면 로케일을 UTF-8 로 지정하세요: `LANG=ko_KR.UTF-8` 또는 `PYTHONUTF8=1`.

## 수동 테스트 시나리오

1. 정상적인 OneFS 접속: `onefs-s3.exe test`
2. 잘못된 endpoint: `endpoint_url`을 틀리게 설정 후 `test`
3. DNS 실패: 존재하지 않는 hostname 설정 후 `test`
4. 잘못된 Access Key: Access Key 변경 후 `test`
5. 잘못된 Secret Key: Secret Key 변경 후 `test`
6. 존재하지 않는 bucket: `bucket_name` 변경 후 `test`
7. 존재하지 않는 object: `info missing/key.txt`
8. SSL 인증서 오류: 사설 CA 미설정 상태에서 `verify_ssl=true`
9. `verify_ssl=false`: 경고 출력 확인
10. `RequestTimeTooSkewed`: 클라이언트 시간을 크게 변경한 뒤 `test`
11. 1,000개 이상의 object list: `list --prefix ...`
12. 대용량 파일 다운로드: `download large/file.bin --output C:\temp\file.bin`
13. 한글 경로 다운로드: `download key --output C:\임시\data.csv`
14. Python이 설치되지 않은 Windows PC에서 `onefs-s3.exe test`

## 로그

로그는 실행 디렉터리 기준 `logs\onefs-s3-YYYYMMDD.log`에 저장됩니다. Secret Key, Authorization header, AWS Signature는 로그에 남기지 않습니다.

## 단위 테스트

```cmd
python -m unittest discover -s tests -v
```
