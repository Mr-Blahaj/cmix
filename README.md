# CMIX-AHP

CMIX-AHP is an experimental, lossless data compressor derived from
[CMIX v21](https://github.com/byronknoll/cmix). It preserves CMIX's existing
context models, preprocessing pipeline, mixers, recurrent byte model, PPMd
model, and arithmetic coder, then adds a small synchronized online residual
mixer to the final bit-probability path.

The goal is deliberately narrow: improve CMIX's final probability estimate
without transmitting a new model and without compromising deterministic,
lossless decoding.

> **Research status:** CMIX-AHP produced an archive four bytes smaller than the
> tested stock CMIX v21 build on `enwik7` with dictionary preprocessing.
> This difference is extremely small and may fall within reasonable
> experimental or build variability. The result requires broader testing
> across machines, compilers, corpora, and independently reproduced builds
> before it should be treated as evidence of a general improvement.

## Repository layout

```text
.
├── dictionary/english.dic   English dictionary used by CMIX preprocessing
├── results/enwik7.csv       Recorded enwik7 benchmark results
├── src/                     CMIX v21 source plus the AHP changes
├── COPYING                  GPL license
└── makefile                 Native and custom-flag builds
```

Local corpora, compiled binaries, benchmark workspaces, and third-party build
trees are intentionally excluded from version control.

## What changed from stock CMIX v21

CMIX-AHP is based on the official CMIX v21 release tag. The upstream baseline
is:

```text
tag: v21
commit: c443679c0773b8ae5b05423827804063d82ae7a8
```

Stock CMIX computes many model predictions, combines them through its existing
mixers and secondary symbol estimation, and sends one final binary probability
to the arithmetic coder:

```text
CMIX models → CMIX mixers/SSE → final probability → arithmetic coder
```

CMIX-AHP inserts one additional stage:

```text
CMIX models → CMIX mixers/SSE → online residual mixer → arithmetic coder
```

### Additional predictor signals

The residual mixer receives four values derived from predictions that CMIX
already computes:

1. CMIX's final mixed bit probability;
2. an aggregate of the PPMd byte-model outputs;
3. an aggregate of CMIX's word-context models;
4. an aggregate of the recurrent byte/LSTM mixer outputs.

The word-model range is recorded when those models are constructed. Predictor
groups are averaged in log-odds space rather than probability space.

### Residual features

Let:

```text
base = logit(final CMIX probability)
```

The online mixer uses:

```text
features = [
  1,
  base,
  logit(PPMd byte) - base,
  logit(word aggregate) - base,
  logit(recurrent byte model) - base
]
```

The final probability is:

```text
logistic(base + weights · features)
```

All weights start at zero. Therefore, before any online learning takes place,
the routed probability is mathematically equal to the stock CMIX prediction.

### Synchronized online update

After each actual bit is known, the residual weights are updated using online
logistic loss:

```text
error = predicted_probability - actual_bit
weight[i] -= 0.00003 * (error * feature[i] + 1e-7 * weight[i])
```

For stability:

- feature values are clipped to `[-6, 6]`;
- residual weights are clipped to `[-2, 2]`;
- a weight decay of `1e-7` is applied.

The encoder and decoder observe the same previous bits in the same order, so
they perform identical updates. No residual weights are stored in the archive.

### Diagnostics

CMIX-AHP prints the final online weights and number of adaptive predictions.
Optional prediction tracing can be enabled with:

```sh
CMIX_AHP_TRACE=trace.csv ./cmix-ahp -c input output.cmix
```

The trace contains the CMIX, byte, word, and recurrent probabilities together
with the observed bit. Tracing is intended for research and significantly
increases output volume.

### Build and portability changes

The source also includes small non-algorithmic changes needed to build and run
the v21 code reliably on the tested Apple Silicon system:

- x86 SIMD declarations in FXCM are guarded on non-x86 targets;
- a `ByteModel` accumulation expression was rewritten to avoid invalid pointer
  formation at the end of its probability array;
- a PPMd context pointer is initialized before use;
- `<cstdint>` is included explicitly where fixed-width integer types are used;
- `NDEBUG` is supplied by the release build instead of being defined inside
  individual model source files;
- the makefile builds only the `cmix-ahp` compressor, omitting CMIX's separate
  enwik9 preprocessing utilities.

### What was not changed

The compression algorithms and data formats of the following CMIX components
remain unchanged:

- arithmetic coder;
- archive header structure;
- dictionary and file-type preprocessing;
- PPMd model logic, apart from the pointer initialization noted above;
- PAQ-derived models;
- recurrent byte/LSTM logic;
- context manager and context models;
- CMIX's existing mixer and SSE update rules.

Because the final probability sequence is different, stock CMIX cannot decode
a CMIX-AHP archive even though the outer header format is unchanged.

## Build

CMIX is designed for high compression ratio rather than low memory usage.
Apple Clang or a recent Clang/GCC toolchain is required.

```sh
make
```

This produces:

```text
./cmix-ahp
```

The default build uses:

```text
-Ofast -march=native -DNDEBUG
```

For a more portable build:

```sh
make clean
make cmix-ahp LFLAGS="-std=c++14 -O3 -DNDEBUG"
```

CMIX maintains synchronized floating-point state. Keep the exact binary used
to create an archive, particularly when using `-Ofast -march=native`.

## Usage

### Recommended text mode: preprocessing and dictionary

```sh
./cmix-ahp -c dictionary/english.dic input.txt output.cmix
```

Decompress using the same dictionary:

```sh
./cmix-ahp -d dictionary/english.dic output.cmix restored.txt
```

### Automatic preprocessing without a dictionary

```sh
./cmix-ahp -c input.txt output.cmix
./cmix-ahp -d output.cmix restored.txt
```

### No preprocessing

```sh
./cmix-ahp -n input.bin output.cmix
./cmix-ahp -d output.cmix restored.bin
```

### Verify lossless restoration

```sh
cmp input.txt restored.txt
shasum -a 256 input.txt restored.txt
```

`cmp` prints nothing when the files are identical. The two SHA-256 values must
also match.

## enwik7 result

The recorded result is available at
[`results/enwik7.csv`](results/enwik7.csv).

The tested input was the 9,999,999-byte `enwik7` corpus. Both CMIX variants
used automatic text preprocessing and the same 411,996-byte English
dictionary.

| Compressor | Compressed size | Bits/byte |
|---|---:|---:|
| **CMIX-AHP** | **1,624,677 bytes** | **1.299741730** |
| Stock CMIX v21 | 1,624,681 bytes | 1.299744930 |

Measured difference:

```text
4 bytes (32 bits), approximately 0.000246%
```

The restored CMIX-AHP output was checked byte-for-byte and by SHA-256.

### Test machine and timing caveat

The result was produced on:

- Mac mini with Apple M4;
- 16 GB unified memory;
- 256 GB internal storage;
- macOS on ARM64.

The machine remained in normal use while the benchmark was running, and other
benchmark activity also occurred during the test period. Consequently,
compression time, decompression time, peak resident memory, and other
environment-sensitive measurements may be affected by system load, memory
pressure, thermal state, filesystem caching, compiler behavior, and background
processes. Archive byte counts are exact; timing and resource measurements
should be independently reproduced under controlled conditions.

### Interpretation

The enwik7 result shows CMIX-AHP outperforming the tested stock CMIX v21 binary
by four bytes. It does **not** establish that CMIX-AHP:

- beats every CMIX fork or build;
- improves every file type or corpus;
- will retain the same lead under another compiler or architecture;
- provides a statistically meaningful general improvement.

The margin is sufficiently small that reasonable experimental inaccuracy or
build variation must be considered. More held-out corpora, repeated runs,
cross-platform builds, and independent reproduction are required.

## License and attribution

CMIX-AHP is derived from CMIX v21 by Byron Knoll and contributors. The project
remains distributed under the GNU General Public License; see
[`COPYING`](COPYING).

The CMIX-AHP changes are experimental research additions and are not presented
as an official upstream CMIX release.
