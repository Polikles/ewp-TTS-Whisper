"""Serve the player example with HTTP byte ranges required by browser media seeking."""

from __future__ import annotations

import argparse
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import BinaryIO

_RANGE = re.compile(r"bytes=(\d*)-(\d*)$")


def parse_byte_range(value: str, size: int) -> tuple[int, int] | None:
    """Return one satisfiable inclusive byte range, or None."""

    match = _RANGE.fullmatch(value.strip())
    if match is None or size <= 0:
        return None
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
    elif last:
        length = min(int(last), size)
        start, end = size - length, size - 1
    else:
        return None
    return (start, end) if start < size and end >= start else None


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """Single-range static handler suitable for local media qualification."""

    range_remaining: int | None = None

    def send_head(self) -> BinaryIO | None:
        path = Path(self.translate_path(self.path))
        if path.is_dir() or not path.is_file():
            return super().send_head()
        try:
            source = path.open("rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        size = path.stat().st_size
        requested = self.headers.get("Range")
        if requested is None:
            source.close()
            return super().send_head()
        byte_range = parse_byte_range(requested, size)
        if byte_range is None:
            source.close()
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        start, end = byte_range
        length = end - start + 1
        source.seek(start)
        self.range_remaining = length
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type", self.guess_type(path.name))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(path.stat().st_mtime))
        self.end_headers()
        return source

    def copyfile(self, source: BinaryIO, outputfile: BinaryIO) -> None:
        if self.range_remaining is None:
            super().copyfile(source, outputfile)
            return
        remaining = self.range_remaining
        while remaining:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    handler = lambda *handler_args, **kwargs: RangeRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(args.directory),
        **kwargs,
    )
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"Serving {args.directory} at http://{args.bind}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
