from urllib.error import URLError

from rich.console import Console

from benchmark import run_benchmark
from cli import CliObserver, load_config, parse_args, print_banner, print_result
from http_client import HttpDownloader


def main() -> int:
    args = parse_args()
    console = Console()
    print_banner(console)

    try:
        config = load_config(url_override=args.url)
        observer = CliObserver(console, config.request_count)
        with observer.progress:
            result = run_benchmark(
                config.url, HttpDownloader(), observer, config.request_count
            )
    except (OSError, URLError, ValueError) as error:
        Console(stderr=True).print(
            f"Download failed: {error}", style="bold red", markup=False
        )
        return 1

    print_result(console, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
