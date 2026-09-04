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

```cmd
build.bat
```

결과:

```text
dist\onefs-s3.exe
```

## 배포

배포 대상 PC에는 기본적으로 다음 파일만 전달합니다.

```text
onefs-s3.exe
config.json
```

사설 CA 인증서가 필요하면 함께 전달합니다.

```text
certs\company-ca.pem
```

배포 대상 PC에는 Python 설치가 필요하지 않습니다.

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
