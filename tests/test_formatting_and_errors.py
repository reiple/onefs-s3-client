import socket
import unittest

from src.s3_client import describe_error, human_size


class FakeClientError(Exception):
    def __init__(self, code: str, status_code: int = 400) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code, "Message": "message"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        }


class FakeEndpointConnectionError(Exception):
    def __init__(self, endpoint_url: str) -> None:
        super().__init__(endpoint_url)
        self.endpoint_url = endpoint_url


class FakeSSLError(Exception):
    pass


class FormattingAndErrorTests(unittest.TestCase):
    def test_human_size_uses_binary_units(self) -> None:
        self.assertEqual(human_size(0), "0 B")
        self.assertEqual(human_size(532 * 1024), "532 KB")
        self.assertEqual(human_size(13_002_342), "12.4 MB")
        self.assertEqual(human_size(5 * 1024 * 1024 * 1024), "5 GB")

    def test_describe_error_identifies_dns_failure(self) -> None:
        message = describe_error(socket.gaierror("name not known"), "https://missing.example")

        self.assertIn("DNS", message)
        self.assertIn("https://missing.example", message)

    def test_describe_error_identifies_ssl_failure(self) -> None:
        message = describe_error(FakeSSLError("certificate verify failed"), "https://onefs.example")

        self.assertIn("SSL", message)
        self.assertIn("인증서", message)

    def test_describe_error_identifies_s3_error_code(self) -> None:
        error = FakeClientError("NoSuchKey", 404)

        message = describe_error(error, "https://onefs.example")

        self.assertIn("NoSuchKey", message)
        self.assertIn("Object를 찾을 수 없습니다", message)

    def test_describe_error_treats_minio_head_object_404_as_missing_object(self) -> None:
        error = FakeClientError("404", 404)

        message = describe_error(error, "https://onefs.example")

        self.assertIn("404", message)
        self.assertIn("Object를 찾을 수 없습니다", message)

    def test_describe_error_identifies_endpoint_connection_error(self) -> None:
        message = describe_error(
            FakeEndpointConnectionError(endpoint_url="https://onefs.example"),
            "https://onefs.example",
        )

        self.assertIn("연결할 수 없습니다", message)
        self.assertIn("Endpoint", message)


if __name__ == "__main__":
    unittest.main()
