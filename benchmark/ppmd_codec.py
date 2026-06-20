#!/usr/bin/env python3
"""Self-describing PPMd-I stream used by the benchmark runner."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pyppmd

MAGIC = b"PPMI"
ORDER = 16
MEMORY = 256 * 1024 * 1024


def compress(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    payload = pyppmd.compress(
        data, max_order=ORDER, mem_size=MEMORY, variant="I"
    )
    destination.write_bytes(
        MAGIC + bytes([ORDER]) + struct.pack(">I", MEMORY) + payload
    )


def decompress(source: Path, destination: Path) -> None:
    archive = source.read_bytes()
    if archive[:4] != MAGIC:
        raise ValueError("not a benchmark PPMd-I archive")
    order = archive[4]
    memory = struct.unpack(">I", archive[5:9])[0]
    data = pyppmd.decompress(
        archive[9:], max_order=order, mem_size=memory, variant="I"
    )
    destination.write_bytes(data)


if len(sys.argv) != 4 or sys.argv[1] not in {"c", "d"}:
    raise SystemExit("usage: ppmd_codec.py c|d INPUT OUTPUT")

operation, source, destination = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
if operation == "c":
    compress(source, destination)
else:
    decompress(source, destination)
