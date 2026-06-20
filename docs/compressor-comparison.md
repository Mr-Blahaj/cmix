# Lossless compressor benchmark: 10 KiB enwik8 slice

Date: June 19, 2026

## Corpus and method

- Input: first exactly 10 KiB (10,240 bytes) of `enwik8`
- SHA-256:
  `25ce06fbf6e86fb6fa38080c1b19e63edb7c0599c829ca5954e57bca1dc2d836`
- Platform: Apple ARM64, 16 GiB RAM, macOS 26.3
- Every decompressed result was compared byte-for-byte and had the same hash.
- Conventional codecs used their strongest practical CLI setting and median
  timing over 30 runs. PPMd used seven runs. PAQ8PX and CMIX used one run
  because each invokes a large research model.
- Times include process startup, archive writing, and archive reading.
- Maximum RSS is the operating system's measured resident memory for the
  compression process.

## Results

All rows have a raw input size of 10,240 bytes. Lower compressed size, bits per
byte, and ratio are better.

| Compressor and setting | Compressed | Ratio | Bits/byte | Compress | Decompress | Compress max RSS |
|---|---:|---:|---:|---:|---:|---:|
| **CMIX-AHP, preprocessing + dictionary** | **2,152 B** | **21.02%** | **1.6812** | 201.24 s | 184.42 s | 7,363 MiB |
| Stock CMIX v21, preprocessing + dictionary | 2,157 B | 21.06% | 1.6852 | 202.71 s | 216.10 s | 7,071 MiB |
| PAQ8PX v215 `-9T` | 2,236 B | 21.84% | 1.7469 | 14.65 s | 14.09 s | 3,131 MiB |
| CMIX-AHP, preprocessing, no dictionary | 2,853 B | 27.86% | 2.2289 | 9.08 s | 9.68 s | 6,885 MiB |
| Stock CMIX v21, preprocessing, no dictionary | 2,857 B | 27.90% | 2.2320 | 8.90 s | 8.99 s | 6,715 MiB |
| Brotli 1.2.0 quality 11 | 3,024 B | 29.53% | 2.3625 | 11.63 ms | 2.26 ms | 3.2 MiB |
| PPMd-I order 16, 256 MiB setting | 3,304 B | 32.27% | 2.5812 | 37.47 ms | 37.19 ms | 14.8 MiB |
| xz/LZMA2 5.8.3 `-9e` | 3,760 B | 36.72% | 2.9375 | 8.03 ms | 5.17 ms | 33.5 MiB |
| Zstandard 1.5.7 `--ultra -22` | 3,764 B | 36.76% | 2.9406 | 6.74 ms | 5.31 ms | 2.2 MiB |
| gzip/Deflate `-9` | 3,814 B | 37.25% | 2.9797 | 4.50 ms | 4.27 ms | 1.8 MiB |
| bzip2 1.0.8 `-9` | 3,824 B | 37.34% | 2.9875 | 5.29 ms | 4.83 ms | 1.8 MiB |
| ZIP/Deflate `-9` | 3,922 B | 38.30% | 3.0641 | 9.91 ms | 4.63 ms | 1.9 MiB |
| LZ4 1.10.0 `-12` | 5,176 B | 50.55% | 4.0438 | 2.27 ms | 2.21 ms | 1.8 MiB |

## Interpretation

### Best archive size

CMIX-AHP produced the smallest archive, five bytes below stock CMIX. This is
not a held-out victory: the AHP coefficients were fitted on this same slice.
Stock CMIX is therefore the strongest untuned result in this table.

The dictionary-assisted CMIX modes require a separate 411,996-byte dictionary
at decompression time. That dictionary is not included in the compressed-size
column. Counting it for this one tiny file would eliminate the apparent space
saving. Dictionary mode makes sense when the same dictionary is already
installed or amortized across many files.

### Best practical ratio

Brotli quality 11 is the practical standout:

- only 867 bytes larger than stock dictionary CMIX;
- approximately 17,000 times faster to compress in this test;
- approximately 95,000 times faster to decompress;
- uses megabytes rather than gigabytes of memory.

PAQ8PX occupies the middle ground. It comes within 79 bytes of stock
dictionary CMIX while taking about 14 seconds and 3.1 GiB. Its `T` mode uses
549,945 bytes of external text-pretraining files, also excluded from the
archive size.

### Speed

LZ4 is fastest but gives the largest output. Among codecs with a more useful
ratio, zstd, gzip, xz, and Brotli all complete in milliseconds. On a 10 KiB
file, process startup is a large part of those measurements.

### PPMd

PPMd-I beats xz, zstd, gzip, bzip2, ZIP, and LZ4 on size, but Brotli is 280
bytes smaller and slightly faster here. The PPMd archive includes a nine-byte
benchmark header containing its order and memory parameters.

## Availability

The local machine did not have a `7z` or `7zz` executable, so the actual 7-Zip
program was not benchmarked. xz provides the LZMA2-family comparison, and
PPMd was measured directly. The packaged fx3-cmix executable was also not
available.

## Reproduction

The commands, PPMd wrapper, raw JSON measurements, archives, and restored files
are all in this directory:

```sh
The benchmark harness and raw artifacts were moved to
`others/results/compressor-benchmark/` during workspace cleanup.
```
