import argparse
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console
    from rich.progress import Task

    from benchmark import BenchmarkResult

MIB = 1024 * 1024
CONFIG_PATH = Path(__file__).resolve().with_name("config.toml")
BANNER = r"""  ___ ___ ___ ___ ___   _____ ___ ___ _____
 / __| _ \ __| __|   \ |_   _| __/ __|_   _|
 \__ \  _/ _|| _|| |) |  | | | _|\__ \ | |
 |___/_| |___|___|___/   |_| |___|___/ |_|"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure download speed over repeated requests."
    )
    parser.add_argument("--url", help="override the URL in config.toml")
    return parser.parse_args()


@dataclass(frozen=True)
class Config:
    url: str
    request_count: int


def load_config(path: Path = CONFIG_PATH, *, url_override: str | None = None) -> Config:
    with path.open("rb") as config_file:
        config = tomllib.load(config_file)

    url = url_override if url_override is not None else config.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"Expected a non-empty URL in {path}")

    count = config.get("request_count")
    if type(count) is not int or count < 1:
        raise ValueError(f"Expected a positive integer request_count in {path}")

    return Config(url, count)


class SpeedColumn(ProgressColumn):
    def render(self, task: Task) -> Text:
        speed = task.speed
        return Text(f"{speed / MIB:.2f} MiB/s" if speed is not None else "-- MiB/s")


class CliObserver:
    def __init__(self, console: Console, request_count: int) -> None:
        self.request_count = request_count
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(binary_units=True),
            SpeedColumn(),
            TimeElapsedColumn(),
            console=console,
            disable=not console.is_terminal,
            transient=True,
        )
        self.task_id = self.progress.add_task("", total=None)

    def request_started(self, number: int) -> None:
        self.progress.reset(
            self.task_id,
            total=None,
            description=f"Request {number}/{self.request_count}",
        )

    def response_started(self, total_bytes: int | None) -> None:
        self.progress.update(self.task_id, total=total_bytes)

    def bytes_received(self, count: int) -> None:
        self.progress.advance(self.task_id, count)


def print_banner(console: Console) -> None:
    console.print(
        BANNER if console.width >= 46 else "SPEED TEST",
        style="bold cyan",
        markup=False,
        highlight=False,
    )


def print_result(console: Console, result: BenchmarkResult) -> None:
    console.print(f"Requests:          {result.request_count}")
    console.print(f"Average time:      {result.average_seconds:.2f} s")
    console.print(f"Downloaded:        {result.total_bytes / MIB:.2f} MiB")
    console.print(
        f"Average speed:     {result.bytes_per_second / MIB:.2f} MiB/s"
        f"  ({result.bytes_per_second * 8 / 1_000_000:.2f} MBit/s)"
    )
