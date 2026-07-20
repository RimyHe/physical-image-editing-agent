from __future__ import annotations

import base64
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def write_sample_png(path: Path, width: int = 256, height: int = 256) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            floor = y > height * 0.58
            if floor:
                r, g, b = 215, 210, 198
            else:
                r, g, b = 236, 240, 244
            in_ball = (x - 128) ** 2 + (y - 130) ** 2 < 42**2
            in_shadow = ((x - 145) / 60) ** 2 + ((y - 181) / 16) ** 2 < 1
            if in_shadow:
                r, g, b = 150, 146, 138
            if in_ball:
                r, g, b = 220, 42, 42
                if x < 116 and y < 119:
                    r, g, b = 255, 120, 120
            row.extend((r, g, b))
        rows.append(bytes(row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = PNG_SIGNATURE + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def png_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Only PNG input is supported by the MVP normalizer.")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def ensure_valid_png(path: Path, min_size: int = 64) -> None:
    data = path.read_bytes()
    width, height = png_size(data)
    if width < min_size or height < min_size:
        raise ValueError(f"Image must be at least {min_size}x{min_size}; got {width}x{height}.")


def image_data_url(path: Path) -> str:
    data = path.read_bytes()
    ensure_valid_png(path)
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def write_b64_image(b64_json: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(b64_json))
