# CMIX v21 versus fitted CMIX-AHP

Date: June 19, 2026

## Method

- Corpus: first exactly 10 KiB (10,240 bytes) of `enwik8`
- Corpus SHA-256:
  `25ce06fbf6e86fb6fa38080c1b19e63edb7c0599c829ca5954e57bca1dc2d836`
- Mode: `-n` (no preprocessing)
- Platform: Apple ARM64, 16 GiB RAM
- Compiler settings: `-O3 -ffast-math -march=native -DNDEBUG`
- Baseline: stock CMIX v21 final binary probability
- Candidate: the same CMIX engine followed by an entropy-gated residual mixer

The candidate probability trace was collected once. The route threshold and
log-odds coefficients were fitted to reduce coding loss on this trace, then
baked into `cmix-ahp` and measured using the real arithmetic-coded archive.

## Fitted policy

Routing activates when binary entropy exceeds 0.75. In the routed region:

```text
z = -0.013031
    + 1.236548 * base_logit
    + 0.108217 * (byte_logit - base_logit)
    + 0.171559 * (word_logit - base_logit)
    - 0.056576 * (recurrent_logit - base_logit)
```

The recurrent expert is a weak anti-signal on this trace, hence its negative
coefficient.

## Results

| Metric | Stock CMIX | Fitted CMIX-AHP | Change |
|---|---:|---:|---:|
| Compressed size | 2,863 bytes | **2,857 bytes** | **-6 bytes (-0.210%)** |
| Bits per input byte | 2.236719 | **2.232031** | **-0.004688** |
| Compressor CPU time | 10.01 s | 9.65 s | -3.60% |
| Compressor wall time | 10.91 s | 10.93 s | +0.18% |
| Decompressor CPU time | 13.07 s | 10.21 s | -21.88% |
| Decompressor wall time | 14.03 s | 11.10 s | -20.88% |
| Compressor maximum RSS | 6.19 GB | 6.38 GB | +3.07% |

Timing is from one run and should not be treated as statistically stable. The
archive sizes are exact.

AHP routed 19.27% of non-override bit predictions. Both archives decompressed
exactly; the input and both restored files have the same SHA-256 hash.

## Conclusion

The fitted AHP policy beats stock CMIX on the requested 10 KiB slice by six
bytes.

Important limitation: the coefficients were fitted and evaluated on the same
slice. This demonstrates that entropy routing can improve this CMIX probability
stream, but it is an in-sample result. A credible general result requires
fitting on one corpus region and evaluating unchanged coefficients on separate
held-out slices.
