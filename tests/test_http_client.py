import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import ClassVar
from unittest.mock import patch
from urllib.error import HTTPError

from http_client import CHUNK_SIZE, HttpDownloader


class RecordingObserver:
    def __init__(self) -> None:
        self.length: int | None = None
        self.chunks: list[int] = []

    def request_started(self, number: int) -> None:
        pass

    def response_started(self, total_bytes: int | None) -> None:
        self.length = total_bytes

    def bytes_received(self, count: int) -> None:
        self.chunks.append(count)


class Handler(BaseHTTPRequestHandler):
    body: ClassVar[bytes] = b"x" * (CHUNK_SIZE + 17)

    def do_GET(self) -> None:
        if self.path == "/error":
            self.send_error(404)
            return

        self.send_response(200)
        if self.path != "/unknown":
            length = len(self.body) + (1 if self.path == "/short" else 0)
            self.send_header("Content-Length", str(length))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class HttpClientTests(unittest.TestCase):
    server: ClassVar[ThreadingHTTPServer]
    thread: ClassVar[Thread]

    @classmethod
    def setUpClass(cls) -> None:
        cls.proxy_patch = patch.dict(
            "os.environ", {"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"}
        )
        cls.proxy_patch.start()
        cls.addClassCleanup(cls.proxy_patch.stop)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.server.server_port}{path}"

    def test_reads_complete_response_in_chunks(self) -> None:
        observer = RecordingObserver()

        total = HttpDownloader().download(self.url("/"), observer)

        self.assertEqual(total, len(Handler.body))
        self.assertEqual(observer.length, len(Handler.body))
        self.assertEqual(observer.chunks, [CHUNK_SIZE, 17])

    def test_reads_response_without_content_length(self) -> None:
        observer = RecordingObserver()

        total = HttpDownloader().download(self.url("/unknown"), observer)

        self.assertEqual(total, len(Handler.body))
        self.assertIsNone(observer.length)

    def test_rejects_incomplete_response(self) -> None:
        with self.assertRaises(OSError):
            HttpDownloader().download(self.url("/short"), RecordingObserver())

    def test_propagates_http_error(self) -> None:
        with self.assertRaises(HTTPError) as error:
            HttpDownloader().download(self.url("/error"), RecordingObserver())

        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_rejects_non_http_url(self) -> None:
        with self.assertRaises(ValueError):
            HttpDownloader().download("file:///tmp/example", RecordingObserver())
