# Adaptive Hierarchical Prediction prototype

This tree is based on upstream CMIX master commit
`9485e5eb25112810b64b7efae7df8ed8a387e8d7` (June 18, 2026).

The final binary probability now passes through an explicit entropy-driven
cascade:

```text
CMIX bit probability
  -> if H(p) > 0.75, admit byte, word, and recurrent residuals
  -> apply a fitted log-odds correction
  -> arithmetic coder
```

Binary entropy is `H(p) = -p log2(p) - (1-p) log2(1-p)`.

The fitted log-odds coefficients are 1.23655 for the base CMIX prediction,
0.10822 for the byte residual, 0.17156 for the word residual, and -0.05658 for
the recurrent residual, plus a -0.01303 bias. The negative recurrent
coefficient is intentional: on the tuning trace it acts as a useful
anti-signal. Routing decisions and coefficients are fixed, deterministic, and
identical in compression and decompression.

## Build and use

```sh
make
./cmix-ahp -n input output.cmix
./cmix-ahp -d output.cmix restored
cmp input restored
```

`cmix-ahp` archives require `cmix-ahp` for decompression. They are deliberately
named separately from stock CMIX archives because the probability sequence is
different.

## Scope and limitation

This prototype implements explicit uncertainty routing at the coding-decision
layer. It does not yet skip computation: all CMIX models continue to update on
every bit so encoder and decoder state remain synchronized. True compute
savings need lazy experts with deterministic state catch-up or independently
updateable sufficient statistics.

The current coefficients were fitted on the first 10 KiB of `enwik8`. They beat
stock CMIX by six bytes on that same slice, so this is currently an in-sample
optimization rather than evidence of generalization.

The LSTM is a recurrent byte predictor, not a pretrained language model.
Accordingly, the last stage is a semantic proxy rather than a full semantic
predictor. Replacing that stage with a synchronized neural language expert is
the natural next experiment.
