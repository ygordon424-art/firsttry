# Stage 2 ROM mechanism screening

- Suite ID: `20261008T035926Z-72140356`
- Classification: `STAGE2_MECHANISM_DEVELOPMENT`
- Runtime: **41.060 s**
- Scope: synthetic mechanism development; not a formal paper result.
- Automatic causal interpretation: **DISABLED**

Every C0–C5 mechanism case used a single-frequency external input with no 2f component. PC1 is an input-detection software control and is not mechanism evidence.

## Spectral robustness record

- Frequency resolution: **0.0799361 Hz**
- Analysis window: **10–20 s**
- Analysis duration: **10 s**
- Analyzed forcing cycles: **8**
- Spectral window: **Hann**
- Nearest-bin errors for C0: f=0.000639489 Hz, 2f=0.00127898 Hz, 3f=0.00191847 Hz

| Case | Purpose / switches | f (Hz) | frequency reference | forcing has 2f | A_f | A_2f | A_3f | A_2f/A_f | A_3f/A_f | stiffness transition | T_min | T_max |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| C0 | linear negative control; linear | 0.8 | FORCING | FALSE | 0.00740231 | 5.12305e-07 | 6.90052e-07 | 6.92088e-05 | 9.32212e-05 | False | N/A | N/A |
| C1 | linear + cubic symmetric stiffness; linear, cubic_stiffness | 0.8 | FORCING | FALSE | 0.00740163 | 5.09514e-07 | 4.59207e-07 | 6.88381e-05 | 6.20413e-05 | False | N/A | N/A |
| C2 | linear + quadratic/asymmetric coupling; linear, quadratic_coupling | 0.8 | FORCING | FALSE | 0.00740231 | 9.16857e-07 | 6.90837e-07 | 0.000123861 | 9.33272e-05 | False | N/A | N/A |
| C3 | linear + tension-only/piecewise stiffness; linear, tension_only | 0.8 | FORCING | FALSE | 0.00678838 | 0.000185538 | 0.000113563 | 0.0273318 | 0.016729 | True | 0.0428485 | 0.232928 |
| C4 | quadratic/asymmetric coupling + tension-only; linear, quadratic_coupling, tension_only | 0.8 | FORCING | FALSE | 0.00678844 | 0.000185746 | 0.000113597 | 0.0273621 | 0.0167339 | True | 0.0428464 | 0.232904 |
| C5 | bending-torsion nonlinear coupling; linear, bending_torsion_coupling | 0.8 | FORCING | FALSE | 0.00740231 | 5.12309e-07 | 6.9009e-07 | 6.92093e-05 | 9.32264e-05 | False | N/A | N/A |
| PC1 | INPUT_2F_DETECTION; linear | 0.8 | FORCING | TRUE | 0.00740234 | 0.000843723 | 8.61046e-07 | 0.113981 | 0.000116321 | False | N/A | N/A |

## Controls

- Linear single-frequency negative control passed: **YES**
- Injected-input-2f detection control passed: **YES**

## Reporting boundary

Rows report signal features only. A larger second-harmonic amplitude than C0 is not automatically assigned to cable slackening, aeroelastic feedback, or any unique physical cause.
