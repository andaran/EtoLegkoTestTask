from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import urlopen

if TYPE_CHECKING:
    from benchmark import ProgressObserver

CHUNK_SIZE = 64 * 1024
DEFAULT_TIMEOUT = 30.0


class HttpDownloader:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def download(self, url: str, observer: ProgressObserver) -> int:
        if urlsplit(url).scheme.lower() not in {"http", "https"}:
            raise ValueError("URL must use HTTP or HTTPS")

        with urlopen(url, timeout=self.timeout) as response:
            length = response.length
            observer.response_started(length)
            total = 0

            while chunk := response.read(CHUNK_SIZE):
                total += len(chunk)
                observer.bytes_received(len(chunk))

            if length is not None and total != length:
                raise OSError(
                    f"Incomplete response: received {total} of {length} bytes"
                )

            return total
