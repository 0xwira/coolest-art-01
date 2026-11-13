#!/usr/bin/env python3
"""Between Water and Fire - entry program for make.fun coolest-art-01.

The artwork ships in this repository as artwork.jpg, a 1024x1024 JPEG:
a demon-masked samurai caught between a water dragon rising from the
waves behind him and a fire dragon wreathed in flames below, painted in
classical ukiyo-e style. This program inspects the file's JPEG structure
(signature, marker walk, start-of-frame dimensions, end-of-image),
inventories its marker segments, checks it against the competition's
image gate (at most 1 MiB, at most 1024x1024 pixels, square format) and
only then publishes it as /output/entry.png.
"""

import hashlib
import os
import struct
import sys

MAX_BYTES = 1_048_576
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

# JPEG markers that carry no length field and no payload.
STANDALONE_MARKERS = {0x01, 0xD8, 0xD9} | set(range(0xD0, 0xD8))
# Start-of-frame markers that hold the frame dimensions.
SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
               0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
SOS_MARKER = 0xDA


def jpeg_dimensions(data):
    """Walk the JPEG marker stream and return (width, height).

    Raises ValueError on any structural surprise so a truncated or
    mislabelled file never reaches the output directory.
    """
    if len(data) < 4 or data[0] != 0xFF or data[1] != 0xD8:
        raise ValueError("missing JPEG start-of-image signature")
    if data[-2] != 0xFF or data[-1] != 0xD9:
        raise ValueError("missing JPEG end-of-image marker")
    pos = 2
    size = len(data)
    while pos + 1 < size:
        if data[pos] != 0xFF:
            raise ValueError(f"expected marker at offset {pos}")
        marker = data[pos + 1]
        pos += 2
        if marker in STANDALONE_MARKERS:
            continue
        if pos + 1 >= size:
            raise ValueError("truncated marker segment")
        (seg_len,) = struct.unpack(">H", data[pos:pos + 2])
        if seg_len < 2 or pos + seg_len > size:
            raise ValueError("marker segment runs past end of file")
        if marker in SOF_MARKERS:
            if seg_len < 7:
                raise ValueError("start-of-frame segment too short")
            (height,) = struct.unpack(">H", data[pos + 3:pos + 5])
            (width,) = struct.unpack(">H", data[pos + 5:pos + 7])
            return width, height
        if marker == SOS_MARKER:
            break  # entropy-coded data follows; dimensions already known or absent
        pos += seg_len
    raise ValueError("no start-of-frame marker found")


def marker_inventory(data):
    """Count JPEG marker segments by marker byte.

    Walks the same marker stream as jpeg_dimensions but keeps going
    until the start-of-scan marker, tallying every segment it passes.
    The inventory is a cheap fingerprint: a structurally odd file (a
    PNG wearing a .jpg name, a truncated export) shows up here as a
    missing or lopsided tally before the art is allowed to ship.
    """
    counts = {}
    pos = 2
    size = len(data)
    while pos + 1 < size:
        if data[pos] != 0xFF:
            raise ValueError(f"expected marker at offset {pos}")
        marker = data[pos + 1]
        counts[marker] = counts.get(marker, 0) + 1
        pos += 2
        if marker in STANDALONE_MARKERS:
            continue
        if marker == SOS_MARKER:
            break
        if pos + 1 >= size:
            raise ValueError("truncated marker segment")
        (seg_len,) = struct.unpack(">H", data[pos:pos + 2])
        if seg_len < 2 or pos + seg_len > size:
            raise ValueError("marker segment runs past end of file")
        pos += seg_len
    return counts


def check_gate(data, width, height):
    """Return a list of gate violations; empty means the art may ship."""
    problems = []
    if len(data) > MAX_BYTES:
        problems.append(f"{len(data)} bytes exceeds the {MAX_BYTES}-byte gate")
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        problems.append(f"{width}x{height} exceeds the {MAX_WIDTH}x{MAX_HEIGHT} gate")
    if width != height:
        problems.append(f"{width}x{height} is not the square format this entry ships")
    return problems


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "artwork.jpg")
    with open(source, "rb") as fh:
        data = fh.read()
    width, height = jpeg_dimensions(data)
    inventory = marker_inventory(data)
    pretty = ", ".join(f"0x{m:02X}x{c}" for m, c in sorted(inventory.items()))
    print(f"marker inventory: {pretty}")
    problems = check_gate(data, width, height)
    if problems:
        for problem in problems:
            print(f"gate check failed: {problem}", file=sys.stderr)
        return 1
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    with open(target, "wb") as fh:
        fh.write(data)
    digest = hashlib.sha256(data).hexdigest()
    # Round-trip check: what landed on disk must parse as the same image.
    with open(target, "rb") as fh:
        landed = fh.read()
    if hashlib.sha256(landed).hexdigest() != digest:
        print("gate check failed: written file differs from the source", file=sys.stderr)
        return 1
    landed_w, landed_h = jpeg_dimensions(landed)
    if (landed_w, landed_h) != (width, height):
        print("gate check failed: written file has different dimensions", file=sys.stderr)
        return 1
    print(f"wrote {target}: {width}x{height}, {len(data)} bytes, sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
