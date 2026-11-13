#!/usr/bin/env python3
"""She Knits the Sky - entry program for make.fun coolest-art-01.

The artwork ships in this repository as artwork.jpg, a 1024x1024 JPEG:
a flat 2D ukiyo-e woodblock-style print on visible canvas grain, where a
colossal golden koi with crochet-lace fins swims across a deep indigo
night sky. A braided strand of yarn unravels from the koi and spirals
down to a rooftop, where a tiny grandmother sits knitting the great fish
into the sky above a miniature lantern-lit village.

This program inspects the file's JPEG structure (signature, marker walk,
start-of-frame dimensions, end-of-image), inventories its marker
segments, estimates the scan's detail density (a soft, low-detail export
must not ship in place of the textured print), checks everything against
the competition's image gate (at most 1 MiB, at most 1024x1024 pixels,
square format) and only then publishes it as /output/entry.png.
"""

import hashlib
import os
import struct
import sys

MAX_BYTES = 1_048_576
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
# Floor for scan_detail_ratio(): the textured print measures ~0.43
# scan bytes per pixel; a flat or blurred stand-in falls far below.
MIN_DETAIL_RATIO = 0.15

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


def scan_detail_ratio(data):
    """Estimate detail density: entropy-coded scan bytes per pixel.

    Everything after the start-of-scan segment is the compressed image
    data itself. Fine texture (canvas grain, crochet patterning, scale
    work) cannot be compressed away, so it shows up as scan bytes; a
    soft or flat export of the same picture collapses to a fraction of
    the size. This is a blunt guard, not a quality score: it exists so a
    low-detail stand-in can never quietly replace the textured print.
    """
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
        if marker == SOS_MARKER:
            scan_bytes = size - 2 - (pos + seg_len)  # minus the EOI marker
            width, height = jpeg_dimensions(data)
            return scan_bytes / (width * height)
        pos += seg_len
    raise ValueError("no start-of-scan marker found")


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
    ratio = scan_detail_ratio(data)
    print(f"detail density: {ratio:.3f} scan bytes/pixel (floor {MIN_DETAIL_RATIO})")
    problems = check_gate(data, width, height)
    if ratio < MIN_DETAIL_RATIO:
        problems.append(f"detail density {ratio:.3f} below the {MIN_DETAIL_RATIO} floor")
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
