import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from rich.console import Console

from benchmark import BenchmarkResult
from cli import CliObserver, load_config, print_banner, print_result
from main import main


class CliTests(unittest.TestCase):
    def test_compact_banner_and_result(self) -> None:
        output = io.StringIO()
        console = Console(file=output, width=30, force_terminal=False)

        print_banner(console)
        print_result(console, BenchmarkResult(10, 10485760, 5.0))

        self.assertIn("SPEED TEST", output.getvalue())
        self.assertIn("10.00 MiB", output.getvalue())
        self.assertIn("2.00 MiB/s", output.getvalue())
        self.assertIn("16.78 MBit/s", output.getvalue())

    def test_observer_tracks_request_and_bytes(self) -> None:
        observer = CliObserver(Console(file=io.StringIO(), force_terminal=False), 7)

        observer.request_started(3)
        observer.response_started(100)
        observer.bytes_received(25)

        task = observer.progress.tasks[0]
        self.assertEqual(task.description, "Request 3/7")
        self.assertEqual(task.total, 100)
        self.assertEqual(task.completed, 25)

    def test_main_returns_error_for_invalid_url(self) -> None:
        with patch("sys.argv", ["main.py", "--url", "file:///tmp/example"]):
            self.assertEqual(main(), 1)

    def test_reads_configured_url(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                'url = "https://example.com/image"\nrequest_count = 3', encoding="utf-8"
            )

            config = load_config(path)
            self.assertEqual(config.url, "https://example.com/image")
            self.assertEqual(config.request_count, 3)

    def test_rejects_missing_url(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(path)

    def test_url_override_and_invalid_counts(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            for value in ("0", "-1", "true", '"2"'):
                path.write_text(f"request_count = {value}", encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    load_config(path, url_override="https://example.com")

            path.write_text("request_count = 2", encoding="utf-8")
            self.assertEqual(
                load_config(path, url_override="https://example.com").url,
                "https://example.com",
            )

    def test_banner_has_one_style(self) -> None:
        output = io.StringIO()
        console = Console(
            file=output, width=80, force_terminal=True, color_system="standard"
        )

        print_banner(console)

        self.assertNotIn("\x1b[35m", output.getvalue())
        self.assertNotIn("\x1b[1;35m", output.getvalue())
