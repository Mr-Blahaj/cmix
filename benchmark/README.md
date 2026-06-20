# Lossless compressor benchmark

This benchmark accepts any single file, discovers the compressors available on
the machine, verifies every decompressed result with SHA-256, and writes a CSV
sorted by compressed size.

## Run everything

From the workspace root:

```sh
python3 benchmark/benchmark.py "/path/to/input.file"
```

CMIX and PAQ are extremely slow and can use several gigabytes of memory.

## Run only practical codecs

```sh
python3 benchmark/benchmark.py "/path/to/input.file" --skip-slow
```

## Choose the output directory

```sh
python3 benchmark/benchmark.py input.txt --output ~/benchmark-results
```

Each run creates a timestamped directory containing:

```text
results.csv       sortable measurements
metadata.json     input hash, unavailable tools, and failures
archives/         compressed outputs
restored/         verified decompressed files
logs/             stdout, stderr, and timing logs
```

## Included configurations

When installed or available locally:

- CMIX-AHP with dictionary preprocessing
- CMIX-AHP with preprocessing but no dictionary
- CMIX-AHP without preprocessing
- Stock CMIX v21 in the same three modes
- PAQ8PX with text pretraining when its model files exist
- PPMd-I
- 7-Zip PPMd and LZMA2
- Brotli quality 11
- Zstandard ultra level 22
- xz/LZMA2 level 9 extreme
- gzip/Deflate level 9
- ZIP/Deflate level 9
- bzip2 level 9
- LZ4 level 12

Missing tools are listed in `metadata.json`; they do not abort the run.

## CSV measurements

The CSV includes raw and compressed sizes, compression ratio, space saving,
bits per byte, compression and decompression time, throughput, peak resident
memory, external dictionary/model size, SHA-256 verification, archive path,
and notes.

Dictionary/model files are reported separately. `compressed_bytes` is the
actual archive size; `total_bytes_if_dependency_counted` adds required external
data such as the CMIX dictionary.

## Optional Python dependency

Direct PPMd-I requires:

```sh
python3 -m pip install pyppmd
```
