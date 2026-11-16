from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


class ProgressObserver(Protocol):
    def request_started(self, number: int) -> None: ...

    def response_started(self, total_bytes: int | None) -> None: ...

    def bytes_received(self, count: int) -> None: ...


class Downloader(Protocol):
    def download(self, url: str, observer: ProgressObserver) -> int: ...


@dataclass(frozen=True)
class BenchmarkResult:
    request_count: int
    total_bytes: int
    total_seconds: float

    @property
    def average_seconds(self) -> float:
        return self.total_seconds / self.request_count

    @property
    def bytes_per_second(self) -> float:
        return self.total_bytes / self.total_seconds


def run_benchmark(
    url: str,
    downloader: Downloader,
    observer: ProgressObserver,
    request_count: int,
    clock: Callable[[], float] = perf_counter,
) -> BenchmarkResult:
    if request_count < 1:
        raise ValueError("Request count must be positive")

    total_bytes = 0
    total_seconds = 0.0

    for number in range(1, request_count + 1):
        observer.request_started(number)
        started = clock()
        total_bytes += downloader.download(url, observer)
        total_seconds += clock() - started

    return BenchmarkResult(request_count, total_bytes, total_seconds)
