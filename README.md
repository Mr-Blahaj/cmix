# CMIX-AHP compressor and decompressor

`cmix-ahp` is a lossless compressor derived from CMIX v21 with an
entropy-gated Adaptive Hierarchical Prediction correction.

One executable handles both operations:

```sh
./cmix-ahp -c input output.cmix
./cmix-ahp -d output.cmix restored
```

## Build

Fast native build:

```sh
make
```

More portable build:

```sh
make clean
make cmix-ahp LFLAGS="-std=c++14 -O3 -DNDEBUG"
```

## Modes

```text
-c  Compress with automatic reversible preprocessing
-n  Compress without preprocessing
-d  Decompress
```

Dictionary-assisted compression:

```sh
./cmix-ahp -c dictionary/english.dic input output.cmix
./cmix-ahp -d dictionary/english.dic output.cmix restored
```

The same dictionary is required when decompressing a dictionary-assisted
archive.

## Binary compatibility

The default native build uses aggressive floating-point optimization. Keep the
exact `cmix-ahp` binary that created an archive and use it for decompression.
For cross-machine archives, build with `-O3` as shown above and use that build
consistently.
