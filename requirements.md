Python을 사용하여 Dell PowerScale OneFS의 S3(Object Storage)에 접속하고 파일을 조회/다운로드할 수 있는 Windows용 프로그램을 작성해줘.

최종 결과물은 **Python이 설치되어 있지 않은 Windows PC 또는 Windows Server에서도 EXE 파일만으로 실행 가능**해야 한다.

아래 요구사항에 따라 프로젝트 전체를 작성해줘.

## 1. 개발 환경

* Python 3.11 기준
* boto3 사용
* botocore 사용
* Windows 10 / Windows 11 / Windows Server 2019 / Windows Server 2022에서 실행 가능하도록 작성
* 최종 배포 파일은 PyInstaller를 사용하여 EXE로 생성
* 대상 PC에는 Python이 설치되어 있지 않다고 가정

가능하면 다음 형태로 빌드한다.

```text
dist/
  onefs-s3.exe
  config.json
```

우선 `--onefile` 방식의 EXE를 사용하고, 라이브러리 호환성 문제 때문에 어렵다면 `--onedir` 방식을 사용할 수 있다.

## 2. 프로젝트 구조

다음과 같이 유지보수가 가능한 구조로 작성해줘.

```text
onefs-s3-client/
├─ src/
│  ├─ main.py
│  ├─ config.py
│  ├─ s3_client.py
│  └─ logger.py
├─ config.json.example
├─ requirements.txt
├─ build.bat
├─ README.md
└─ .gitignore
```

필요하다면 구조를 개선해도 된다.

## 3. OneFS S3 접속 설정

접속 정보는 Python 코드에 하드코딩하지 말고 `config.json`에서 읽도록 한다.

예:

```json
{
  "endpoint_url": "https://onefs-s3.example.com",
  "access_key": "ACCESS_KEY",
  "secret_key": "SECRET_KEY",
  "region_name": "us-east-1",
  "bucket_name": "my-bucket",
  "verify_ssl": true,
  "ca_bundle": ""
}
```

다음 설정을 지원해야 한다.

* endpoint URL
* Access Key
* Secret Key
* Region
* Bucket
* SSL 인증서 검증 여부
* 사설 CA 인증서를 사용하는 경우 CA 인증서 파일 경로 지정

OneFS가 자체 서명 인증서를 사용하는 환경도 고려한다.

예를 들어:

```json
"verify_ssl": false
```

또는

```json
"verify_ssl": true,
"ca_bundle": "certs/company-ca.pem"
```

형태를 지원한다.

Secret Key가 로그에 출력되지 않도록 주의한다.

## 4. boto3 S3 Client

OneFS S3와 호환되도록 boto3 client를 생성한다.

가능하면 다음 옵션을 고려한다.

```python
from botocore.config import Config

Config(
    signature_version="s3v4",
    s3={
        "addressing_style": "path"
    },
    retries={
        "max_attempts": 3,
        "mode": "standard"
    }
)
```

OneFS 환경에서는 Virtual Hosted Style보다 Path Style이 필요한 경우가 있으므로 설정 가능하도록 한다.

config.json에 다음 옵션을 추가해도 된다.

```json
"s3_addressing_style": "path"
```

## 5. 프로그램 기능

CLI 프로그램으로 작성한다.

예:

```cmd
onefs-s3.exe test
```

OneFS S3 연결 테스트.

```cmd
onefs-s3.exe buckets
```

접근 가능한 bucket 목록 출력.

```cmd
onefs-s3.exe list
```

config.json에 설정된 bucket의 object 목록 출력.

```cmd
onefs-s3.exe list --prefix folder1/
```

특정 prefix의 object 목록 출력.

```cmd
onefs-s3.exe download test/data.csv
```

Object 다운로드.

```cmd
onefs-s3.exe download test/data.csv --output C:\temp\data.csv
```

지정된 위치에 다운로드.

```cmd
onefs-s3.exe info test/data.csv
```

Object metadata 조회.

가능하면 다음 기능도 구현한다.

```cmd
onefs-s3.exe upload C:\temp\data.csv --key test/data.csv
```

파일 업로드.

## 6. Object 목록 조회

S3의 object가 1,000개를 초과하는 경우도 정상적으로 처리하도록 boto3 paginator를 사용한다.

예:

```python
client.get_paginator("list_objects_v2")
```

목록에는 최소 다음 정보를 표시한다.

```text
Key
Size
LastModified
```

예:

```text
test/file1.csv    12.4 MB    2026-09-05 10:10:20
test/file2.csv    532 KB     2026-09-05 10:11:30
```

파일 크기는 사람이 읽기 쉬운 KB / MB / GB 단위로 표시한다.

## 7. 다운로드

큰 파일도 메모리에 전체를 올리지 않고 다운로드할 수 있도록 한다.

가능하면 boto3의

```python
download_file()
```

또는 TransferConfig를 사용한다.

다운로드 중 오류가 발생하면 incomplete 파일을 어떻게 처리할지도 고려한다.

다운로드 대상 디렉터리가 없으면 자동으로 생성한다.

## 8. 네트워크 및 오류 처리

다음 오류들을 구분하여 사용자에게 이해하기 쉬운 메시지를 출력한다.

* DNS Resolution 실패
* Connection timeout
* Connection refused
* SSL Certificate 오류
* 401 Unauthorized
* 403 AccessDenied
* 404 NoSuchKey
* NoSuchBucket
* SignatureDoesNotMatch
* RequestTimeTooSkewed
* EndpointConnectionError
* ReadTimeoutError
* ClientError

예:

```text
[ERROR] OneFS S3 서버에 연결할 수 없습니다.
Endpoint: https://onefs-s3.example.com

가능한 원인:
- DNS 설정
- 방화벽
- Endpoint URL
- OneFS S3 서비스 상태
```

또는:

```text
[ERROR] RequestTimeTooSkewed

클라이언트와 OneFS 서버의 시간이 크게 차이납니다.

Client Time : ...
Server Time : ...
Difference  : ... seconds
```

가능하다면 HTTP Response의 `Date` 헤더를 이용해 OneFS와 클라이언트의 시간 차이를 확인하는 진단 기능도 추가한다.

단, boto3 SigV4 서명 시간을 비정상적으로 강제 조작하는 방식은 기본 동작으로 사용하지 않는다.

## 9. 연결 테스트

다음 명령을 구현한다.

```cmd
onefs-s3.exe test
```

다음 항목을 순서대로 검사한다.

```text
[1] Config 파일 확인
[2] Endpoint URL 확인
[3] DNS Resolution
[4] TCP 연결
[5] SSL 인증서
[6] S3 API 연결
[7] Bucket 접근
```

예:

```text
OneFS S3 Connection Test

Endpoint : https://onefs-s3.example.com
Bucket   : test-bucket

[OK] Configuration
[OK] DNS Resolution
[OK] TCP Connection
[OK] SSL Connection
[OK] S3 Authentication
[OK] Bucket Access

Connection test completed successfully.
```

실패한 단계가 있으면 정확한 원인을 출력한다.

## 10. 로그

프로그램 실행 로그를 다음 위치에 저장한다.

```text
logs/
```

예:

```text
logs/onefs-s3-20260905.log
```

로그에는 다음을 포함한다.

* 실행 시간
* 명령
* endpoint
* bucket
* API 호출 결과
* 예외 stack trace

하지만 다음 정보는 절대 출력하지 않는다.

```text
secret_key
Authorization header
AWS Signature
```

Access Key도 필요하면 일부 masking한다.

예:

```text
ABCD********WXYZ
```

## 11. config.json 위치

EXE와 동일한 디렉터리의 `config.json`을 기본으로 사용한다.

PyInstaller로 실행할 때 `__file__` 기준이 아니라 **실행 파일이 존재하는 디렉터리**를 기준으로 찾도록 한다.

예:

```python
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent
```

필요하면 프로젝트 구조에 맞게 개선한다.

사용자가 다음과 같이 별도의 설정 파일을 지정할 수도 있도록 한다.

```cmd
onefs-s3.exe --config C:\config\onefs.json test
```

## 12. PyInstaller

PyInstaller를 사용하여 Python이 설치되지 않은 PC에서도 실행할 수 있도록 한다.

`build.bat`을 작성한다.

예:

```bat
@echo off

python -m pip install -r requirements.txt
python -m PyInstaller ^
  --clean ^
  --onefile ^
  --name onefs-s3 ^
  src\main.py
```

boto3/botocore 관련 hidden import나 metadata가 필요하면 실제 필요한 옵션을 추가한다.

빌드 결과:

```text
dist\onefs-s3.exe
```

가 생성되어야 한다.

빌드 후 다음과 같이 사용할 수 있어야 한다.

```cmd
cd dist

onefs-s3.exe test
onefs-s3.exe list
```

## 13. requirements.txt

최소한 다음 라이브러리를 포함한다.

```text
boto3
botocore
pyinstaller
```

필요한 라이브러리가 있으면 추가한다.

버전 충돌 가능성을 고려해서 호환되는 버전을 지정해도 된다.

## 14. 보안

다음 원칙을 적용한다.

* Access Key / Secret Key 코드 하드코딩 금지
* Secret Key 로그 출력 금지
* Authorization Header 로그 출력 금지
* config.json에는 민감정보가 있으므로 `.gitignore`에 추가
* `config.json.example`만 Git에 포함
* `verify_ssl=false` 사용 시 경고 출력

예:

```text
[WARNING] SSL certificate verification is disabled.
This configuration should only be used in a trusted network.
```

## 15. README.md

README에는 다음 내용을 포함한다.

### 개발 환경 준비

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 실행

```cmd
python src\main.py test
```

### 빌드

```cmd
build.bat
```

### 배포

배포 대상 PC에는 다음 파일만 전달하면 되도록 한다.

```text
onefs-s3.exe
config.json
```

필요하다면 CA 인증서도 포함한다.

```text
certs\company-ca.pem
```

Python 설치는 필요하지 않아야 한다.

## 16. 코드 품질

다음을 지켜줘.

* Python type hint 사용
* 함수별 역할 명확하게 분리
* 긴 함수를 최소화
* Exception 처리 명확하게 구현
* 공통 설정과 S3 로직 분리
* logging 모듈 사용
* pathlib 사용
* argparse 또는 동등한 CLI 라이브러리 사용
* Windows 경로 처리 고려
* UTF-8 파일명 처리
* 한글 경로에서도 가능한 한 정상 동작
* Ctrl+C 처리

## 17. 테스트

최소한 다음 시나리오를 테스트할 수 있도록 작성한다.

1. 정상적인 OneFS 접속
2. 잘못된 endpoint
3. DNS 실패
4. 잘못된 Access Key
5. 잘못된 Secret Key
6. 존재하지 않는 bucket
7. 존재하지 않는 object
8. SSL 인증서 오류
9. verify_ssl=false
10. RequestTimeTooSkewed
11. 1,000개 이상의 object list
12. 대용량 파일 다운로드
13. 한글 경로 다운로드
14. Python이 설치되지 않은 Windows PC에서 EXE 실행

가능하면 unit test도 추가한다.

## 18. 최종 작업 방식

먼저 전체 프로젝트 구조와 설계를 간단히 설명하고 바로 실제 파일들을 생성해줘.

설명만 하지 말고 다음 파일을 실제로 작성해야 한다.

```text
src/main.py
src/config.py
src/s3_client.py
src/logger.py
config.json.example
requirements.txt
build.bat
README.md
.gitignore
```

필요한 파일이 더 있으면 추가한다.

작업 완료 후 다음을 수행해줘.

1. 생성한 파일 목록 출력
2. 각 파일의 역할 설명
3. 실행 방법 설명
4. PyInstaller 빌드 방법 설명
5. 빌드 과정에서 발생할 수 있는 문제점 확인
6. 코드 syntax 및 import 오류 확인
7. 가능하다면 프로그램을 실제로 빌드하여 EXE 생성 여부 확인
8. 문제가 발견되면 수정 후 다시 검증

중간에 나에게 코드를 복사하라고 요구하지 말고, 현재 Claude Code 작업 디렉터리에 프로젝트 파일을 직접 생성 및 수정해줘.

