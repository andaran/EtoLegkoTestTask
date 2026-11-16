import unittest
from typing import TYPE_CHECKING

from benchmark import ProgressObserver, run_benchmark

if TYPE_CHECKING:
    from collections.abc import Iterator


class RecordingObserver:
    def __init__(self) -> None:
        self.requests: list[int] = []
        self.sizes: list[int | None] = []
        self.chunks: list[int] = []

    def request_started(self, number: int) -> None:
        self.requests.append(number)

    def response_started(self, total_bytes: int | None) -> None:
        self.sizes.append(total_bytes)

    def bytes_received(self, count: int) -> None:
        self.chunks.append(count)


class FakeDownloader:
    def __init__(self, fail_on: int | None = None) -> None:
        self.urls: list[str] = []
        self.fail_on = fail_on

    def download(self, url: str, observer: ProgressObserver) -> int:
        self.urls.append(url)
        if len(self.urls) == self.fail_on:
            raise OSError("download failed")

        observer.response_started(100)
        observer.bytes_received(100)
        return 100


class CallableClock:
    def __init__(self, values: Iterator[float]) -> None:
        self.values = values

    def __call__(self) -> float:
        return next(self.values)


class BenchmarkTests(unittest.TestCase):
    def test_calculates_statistics_for_ten_requests(self) -> None:
        downloader = FakeDownloader()
        observer = RecordingObserver()
        clock = CallableClock(iter(float(value) for value in range(20)))

        result = run_benchmark("https://example.com", downloader, observer, 10, clock)

        self.assertEqual(downloader.urls, ["https://example.com"] * 10)
        self.assertEqual(observer.requests, list(range(1, 11)))
        self.assertEqual(observer.chunks, [100] * 10)
        self.assertEqual(result.request_count, 10)
        self.assertEqual(result.total_bytes, 1000)
        self.assertEqual(result.average_seconds, 1.0)
        self.assertEqual(result.bytes_per_second, 100.0)

    def test_stops_on_download_error(self) -> None:
        downloader = FakeDownloader(fail_on=3)
        observer = RecordingObserver()
        clock = CallableClock(iter([0.0, 1.0, 2.0, 3.0, 4.0]))

        with self.assertRaisesRegex(OSError, "download failed"):
            run_benchmark("https://example.com", downloader, observer, 10, clock)

        self.assertEqual(len(downloader.urls), 3)
        self.assertEqual(observer.requests, [1, 2, 3])

    def test_configurable_request_count(self) -> None:
        downloader = FakeDownloader()
        observer = RecordingObserver()
        clock = CallableClock(iter([0.0, 1.0, 2.0, 3.0]))

        result = run_benchmark("https://example.com", downloader, observer, 2, clock)

        self.assertEqual(result.request_count, 2)
        self.assertEqual(result.total_bytes, 200)
        self.assertEqual(observer.requests, [1, 2])

    def test_rejects_zero_requests(self) -> None:
        with self.assertRaises(ValueError):
            run_benchmark(
                "https://example.com", FakeDownloader(), RecordingObserver(), 0
            )
