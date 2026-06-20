#!/usr/bin/env python3
"""Benchmark available lossless compressors and write results.csv."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TIME = Path("/usr/bin/time")
PPMD = HERE / "ppmd_codec.py"


@dataclass
class Codec:
    name: str
    extension: str
    compress: list[str]
    decompress: list[str]
    family: str
    repetitions: int = 5
    notes: str = ""
    external_bytes: int = 0


def executable(name: str, *fallbacks: Path) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for candidate in fallbacks:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_command(command: list[str], source: Path, archive: Path,
                   restored: Path) -> list[str]:
    return [
        value.format(src=str(source), arc=str(archive), out=str(restored))
        for value in command
    ]


def timed(command: list[str], repetitions: int, log_path: Path) -> tuple[float, int]:
    samples: list[float] = []
    rss_samples: list[int] = []
    logs: list[str] = []
    for _ in range(repetitions):
        start = time.perf_counter()
        result = subprocess.run(
            [str(TIME), "-lp", *command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        elapsed = time.perf_counter() - start
        stderr = result.stderr.decode("utf-8", errors="replace")
        stdout = result.stdout.decode("utf-8", errors="replace")
        memory = re.search(r"(\d+)\s+maximum resident set size", stderr)
        samples.append(elapsed)
        rss_samples.append(int(memory.group(1)) if memory else 0)
        logs.append(stdout + stderr)
    log_path.write_text("\n\n===== repetition =====\n".join(logs))
    return statistics.median(samples), int(statistics.median(rss_samples))


def discover_codecs() -> tuple[list[Codec], list[str]]:
    codecs: list[Codec] = []
    unavailable: list[str] = []

    cmix_ahp = executable("cmix-ahp", ROOT / "cmix-ahp/cmix-ahp")
    ahp_dictionary = ROOT / "cmix-ahp/dictionary/english.dic"
    stock_cmix = executable(
        "cmix",
        ROOT / "others/cmix-v21/cmix",
        ROOT / "others/cmix-v21-src/cmix",
    )
    stock_dictionary = ROOT / "others/cmix-v21/english.dic"
    paq8px = executable("paq8px", ROOT / "others/paq8px")

    if cmix_ahp:
        codecs.extend([
            Codec(
                "CMIX-AHP: preprocessing + dictionary", "cmix-ahp-dict",
                [cmix_ahp, "-c", str(ahp_dictionary), "{src}", "{arc}"],
                [cmix_ahp, "-d", str(ahp_dictionary), "{arc}", "{out}"],
                "CMIX", 1,
                "Dictionary must be available to the decoder.",
                ahp_dictionary.stat().st_size if ahp_dictionary.is_file() else 0,
            ),
            Codec(
                "CMIX-AHP: preprocessing, no dictionary", "cmix-ahp-pre",
                [cmix_ahp, "-c", "{src}", "{arc}"],
                [cmix_ahp, "-d", "{arc}", "{out}"],
                "CMIX", 1,
            ),
            Codec(
                "CMIX-AHP: no preprocessing", "cmix-ahp-raw",
                [cmix_ahp, "-n", "{src}", "{arc}"],
                [cmix_ahp, "-d", "{arc}", "{out}"],
                "CMIX", 1,
            ),
        ])
    else:
        unavailable.append("CMIX-AHP")

    if stock_cmix:
        codecs.extend([
            Codec(
                "Stock CMIX v21: preprocessing, no dictionary", "cmix-stock-pre",
                [stock_cmix, "-c", "{src}", "{arc}"],
                [stock_cmix, "-d", "{arc}", "{out}"],
                "CMIX", 1,
            ),
            Codec(
                "Stock CMIX v21: no preprocessing", "cmix-stock-raw",
                [stock_cmix, "-n", "{src}", "{arc}"],
                [stock_cmix, "-d", "{arc}", "{out}"],
                "CMIX", 1,
            ),
        ])
        if stock_dictionary.is_file():
            codecs.append(Codec(
                "Stock CMIX v21: preprocessing + dictionary", "cmix-stock-dict",
                [stock_cmix, "-c", str(stock_dictionary), "{src}", "{arc}"],
                [stock_cmix, "-d", str(stock_dictionary), "{arc}", "{out}"],
                "CMIX", 1,
                "Dictionary must be available to the decoder.",
                stock_dictionary.stat().st_size,
            ))
    else:
        unavailable.append("Stock CMIX v21")

    commands = {
        "gzip": Codec(
            "gzip/Deflate -9", "gz",
            ["/bin/sh", "-c", 'gzip -9 -n -c "$1" > "$2"', "sh", "{src}", "{arc}"],
            ["/bin/sh", "-c", 'gzip -d -c "$1" > "$2"', "sh", "{arc}", "{out}"],
            "Deflate",
        ),
        "bzip2": Codec(
            "bzip2 -9", "bz2",
            ["/bin/sh", "-c", 'bzip2 -9 -c "$1" > "$2"', "sh", "{src}", "{arc}"],
            ["/bin/sh", "-c", 'bzip2 -d -c "$1" > "$2"', "sh", "{arc}", "{out}"],
            "BWT",
        ),
        "xz": Codec(
            "xz/LZMA2 -9e", "xz",
            ["/bin/sh", "-c", 'xz -9e -c "$1" > "$2"', "sh", "{src}", "{arc}"],
            ["/bin/sh", "-c", 'xz -d -c "$1" > "$2"', "sh", "{arc}", "{out}"],
            "LZMA2",
        ),
        "zstd": Codec(
            "Zstandard --ultra -22", "zst",
            ["/bin/sh", "-c", 'zstd --ultra -22 -q -f -c "$1" > "$2"', "sh", "{src}", "{arc}"],
            ["/bin/sh", "-c", 'zstd -d -q -f -c "$1" > "$2"', "sh", "{arc}", "{out}"],
            "Zstandard",
        ),
        "brotli": Codec(
            "Brotli quality 11", "br",
            ["brotli", "-q", "11", "-w", "24", "-f", "-o", "{arc}", "{src}"],
            ["brotli", "-d", "-f", "-o", "{out}", "{arc}"],
            "Brotli",
        ),
        "lz4": Codec(
            "LZ4 -12", "lz4",
            ["lz4", "-12", "-q", "-f", "{src}", "{arc}"],
            ["lz4", "-d", "-q", "-f", "{arc}", "{out}"],
            "LZ4",
        ),
        "zip": Codec(
            "ZIP/Deflate -9", "zip",
            ["/bin/sh", "-c",
             'rm -f "$2"; cd "$(dirname "$1")"; zip -9 -X -q -j "$2" "$(basename "$1")"',
             "sh", "{src}", "{arc}"],
            ["/bin/sh", "-c", 'unzip -p "$1" > "$2"', "sh", "{arc}", "{out}"],
            "Deflate", notes="Includes ZIP container and filename overhead.",
        ),
    }
    for command, codec in commands.items():
        if shutil.which(command):
            codecs.append(codec)
        else:
            unavailable.append(codec.name)

    seven_zip = executable("7zz") or executable("7z")
    if seven_zip:
        codecs.extend([
            Codec(
                "7-Zip LZMA2 -mx=9", "7z-lzma2",
                ["/bin/sh", "-c",
                 f'rm -f "$2"; "{seven_zip}" a -t7z -m0=lzma2 -mx=9 '
                 '-mmt=1 -bd -y "$2" "$1"',
                 "sh", "{src}", "{arc}"],
                [seven_zip, "e", "-so", "{arc}"],
                "LZMA2",
                notes="7z container overhead included.",
            ),
            Codec(
                "7-Zip PPMd -mx=9", "7z-ppmd",
                ["/bin/sh", "-c",
                 f'rm -f "$2"; "{seven_zip}" a -t7z -m0=ppmd -mx=9 '
                 '-mmt=1 -bd -y "$2" "$1"',
                 "sh", "{src}", "{arc}"],
                ["/bin/sh", "-c", f'"{seven_zip}" e -so "$1" > "$2"',
                 "sh", "{arc}", "{out}"],
                "PPMd",
                notes="7z container overhead included.",
            ),
        ])
    else:
        unavailable.append("7-Zip LZMA2 and PPMd")

    try:
        import pyppmd  # noqa: F401
        codecs.append(Codec(
            "PPMd-I order 16, 256 MiB", "ppmd",
            [sys.executable, str(PPMD), "c", "{src}", "{arc}"],
            [sys.executable, str(PPMD), "d", "{arc}", "{out}"],
            "PPMd", 3,
            "Includes a 9-byte parameter header.",
        ))
    except ImportError:
        unavailable.append("PPMd-I (install pyppmd)")

    if paq8px:
        pretraining = [
            ROOT / "others/english.dic",
            ROOT / "others/english.exp",
            ROOT / "others/english.emb",
        ]
        flag = "-9T" if all(path.is_file() for path in pretraining) else "-9"
        external = sum(path.stat().st_size for path in pretraining if path.is_file())
        codecs.append(Codec(
            f"PAQ8PX v215 {flag}", "paq8px",
            [paq8px, flag, "{src}", "{arc}"],
            [paq8px, "-d", "{arc}", "{out}"],
            "PAQ", 1,
            "Text pretraining files are external." if flag == "-9T" else "",
            external if flag == "-9T" else 0,
        ))
    else:
        unavailable.append("PAQ8PX")

    return codecs, unavailable


def run_codec(codec: Codec, source: Path, output: Path,
              repetitions: int) -> dict[str, object]:
    safe = re.sub(r"[^a-z0-9]+", "-", codec.extension.lower()).strip("-")
    archive = output / "archives" / f"{source.name}.{safe}"
    restored = output / "restored" / f"{source.name}.{safe}.restored"
    logs = output / "logs"
    archive.unlink(missing_ok=True)
    restored.unlink(missing_ok=True)

    compress = format_command(codec.compress, source, archive, restored)
    decompress = format_command(codec.decompress, source, archive, restored)
    runs = repetitions if codec.repetitions > 1 else 1

    ctime, crss = timed(compress, runs, logs / f"{safe}-compress.log")
    if not archive.is_file():
        raise RuntimeError(f"{codec.name} did not create an archive")

    # 7-Zip LZMA2's direct command emits to stdout, unlike the shell-wrapped
    # PPMd command. Wrap it here so all decoders create a restored file.
    if codec.name == "7-Zip LZMA2 -mx=9":
        decompress = [
            "/bin/sh", "-c", f'"{decompress[0]}" e -so "$1" > "$2"',
            "sh", str(archive), str(restored),
        ]
    dtime, drss = timed(decompress, runs, logs / f"{safe}-decompress.log")

    source_hash = sha256(source)
    restored_hash = sha256(restored)
    if source_hash != restored_hash:
        raise RuntimeError(f"{codec.name} failed SHA-256 verification")

    raw = source.stat().st_size
    compressed = archive.stat().st_size
    return {
        "compressor": codec.name,
        "family": codec.family,
        "status": "ok",
        "raw_bytes": raw,
        "compressed_bytes": compressed,
        "ratio_percent": 100.0 * compressed / raw if raw else 0.0,
        "space_saving_percent": 100.0 * (raw - compressed) / raw if raw else 0.0,
        "bits_per_byte": 8.0 * compressed / raw if raw else 0.0,
        "compress_seconds": ctime,
        "decompress_seconds": dtime,
        "compress_mib_per_second": raw / 1048576.0 / ctime if ctime else 0.0,
        "decompress_mib_per_second": raw / 1048576.0 / dtime if dtime else 0.0,
        "compress_max_rss_mib": crss / 1048576.0,
        "decompress_max_rss_mib": drss / 1048576.0,
        "external_dependency_bytes": codec.external_bytes,
        "total_bytes_if_dependency_counted": compressed + codec.external_bytes,
        "sha256_verified": "yes",
        "archive": str(archive),
        "notes": codec.notes,
    }


FIELDS = [
    "rank", "compressor", "family", "status", "raw_bytes", "compressed_bytes",
    "ratio_percent", "space_saving_percent", "bits_per_byte",
    "compress_seconds", "decompress_seconds", "compress_mib_per_second",
    "decompress_mib_per_second", "compress_max_rss_mib",
    "decompress_max_rss_mib", "external_dependency_bytes",
    "total_bytes_if_dependency_counted", "sha256_verified", "archive", "notes",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark all available lossless compressors."
    )
    parser.add_argument("input", type=Path, help="file to benchmark")
    parser.add_argument(
        "--output", type=Path, default=HERE / "runs",
        help="output directory (default: benchmark/runs)",
    )
    parser.add_argument(
        "--repetitions", type=int, default=5,
        help="median repetitions for fast codecs (default: 5)",
    )
    parser.add_argument(
        "--skip-slow", action="store_true",
        help="skip CMIX and PAQ compressors",
    )
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"input file not found: {source}")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = args.output.expanduser().resolve() / f"{source.stem}-{stamp}"
    for directory in ("archives", "restored", "logs"):
        (output / directory).mkdir(parents=True, exist_ok=True)

    codecs, unavailable = discover_codecs()
    if args.skip_slow:
        codecs = [codec for codec in codecs if codec.family not in {"CMIX", "PAQ"}]

    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for index, codec in enumerate(codecs, 1):
        print(f"[{index}/{len(codecs)}] {codec.name}", flush=True)
        try:
            rows.append(run_codec(codec, source, output, args.repetitions))
        except Exception as error:
            failures.append(f"{codec.name}: {error}")
            rows.append({
                "compressor": codec.name,
                "family": codec.family,
                "status": "failed",
                "notes": str(error),
            })

    successful = sorted(
        (row for row in rows if row.get("status") == "ok"),
        key=lambda row: int(row["compressed_bytes"]),
    )
    failed = [row for row in rows if row.get("status") != "ok"]
    rows = successful + failed
    for rank, row in enumerate(successful, 1):
        row["rank"] = rank

    csv_path = output / "results.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    metadata = {
        "input": str(source),
        "input_bytes": source.stat().st_size,
        "input_sha256": sha256(source),
        "timestamp": stamp,
        "repetitions": args.repetitions,
        "unavailable": unavailable,
        "failures": failures,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"\nCSV: {csv_path}")
    if unavailable:
        print("Unavailable:", ", ".join(unavailable))
    if failures:
        print("Failures:", "; ".join(failures))


if __name__ == "__main__":
    main()
