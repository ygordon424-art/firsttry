# Stage 2 mechanism falsification

- Suite ID: `20261008T095650Z-e2cdf31b`
- Classification: `STAGE2_MECHANISM_DEVELOPMENT`
- Total runtime: **9.499 s**
- Parameter optimization/search: **NOT PERFORMED**
- Interpretation scope: numerical mechanism capability and model-form sensitivity only.
- Clean-HEAD verification (`8829325`): **35 tests passed in 4.50 s**

| Case | Mode/control | Response | A_f | A_2f | A_3f | A_2f/A_f | min T | T<=0 fraction | softened fraction | transitions | f2/f1 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | BILATERAL_LINEAR | z | 0.00665452 | 3.87338e-07 | 1.21834e-06 | 5.82068e-05 | -0.0167678 | 0.0629685 | 0 | 0 | 1.50152 |
| B1 | LOW_TENSION_SOFTENING/ABRUPT_PIECEWISE | z | 0.00678838 | 0.000185538 | 0.000113563 | 0.0273318 | 0.0428485 | 0 | 0.34033 | 32 | 1.50152 |
| B2 | LOW_TENSION_SOFTENING/SMOOTH_TRANSITION | z | 0.00678984 | 0.000177845 | 9.9002e-05 | 0.0261929 | 0.0366905 | 0 | 0.33933 | 32 | 1.50152 |
| C_TRUE_1 | TRUE_TENSION_ONLY | z | 0.00665452 | 3.87338e-07 | 1.21834e-06 | 5.82068e-05 | 0.0832322 | 0 | 0 | 0 | 1.50152 |
| C_TRUE_2 | TRUE_TENSION_ONLY | z | 0.00693696 | 0.000306941 | 8.48466e-05 | 0.0442472 | 0 | 0.44078 | 0 | 32 | 1.50152 |
| IR0 | SYNTHETIC INTERNAL-RESONANCE CONTROL: linear near 1:2 | theta | 0 | 0 | 0 | N/A | N/A | 0 | 0 | 0 | 2 |
| IR1 | SYNTHETIC INTERNAL-RESONANCE CONTROL: quadratic bending-torsion coupling near 1:2 | theta | 4.7611e-07 | 0.0382397 | 6.27071e-07 | 80317.1 | N/A | 0 | 0 | 0 | 2 |
| IR2 | SYNTHETIC INTERNAL-RESONANCE CONTROL: same coupling detuned | theta | 5.43234e-08 | 0.00487811 | 5.29688e-08 | 89797.7 | N/A | 0 | 0 | 0 | 1.6 |
| R_HALF_DT | LOW_TENSION_SOFTENING/ABRUPT_PIECEWISE | z | 0.00678838 | 0.000185538 | 0.000113562 | 0.0273317 | 0.0428485 | 0 | 0.34033 | 32 | 1.50152 |
| R_ALT_SOLVER | LOW_TENSION_SOFTENING/ABRUPT_PIECEWISE | z | 0.00678838 | 0.000185538 | 0.000113563 | 0.0273317 | 0.0428485 | 0 | 0.34033 | 32 | 1.50152 |
| R_16_CYCLES | LOW_TENSION_SOFTENING/ABRUPT_PIECEWISE | z | 0.00678738 | 0.000185611 | 0.000114469 | 0.0273465 | 0.0428485 | 0 | 0.341553 | 48 | 1.50152 |

## Required falsification questions

1. **Dependence on a positive-tension threshold:** **YES for this synthetic model form.** B1 was `0.0273318`, whereas C_TRUE_1 was `5.82068e-05` with no zero-tension transition. The strong C3-like response therefore did not persist when the positive threshold was removed; this does not identify a physical cable mechanism.
2. **Abrupt versus smooth transition:** The relative difference in `A_2f/A_f` is **0.0416694** (fraction). The smooth model retained most of the response, so the amplitude is not explained solely by a tangent-stiffness discontinuity. This is model-form sensitivity, not causal confirmation.
3. **TRUE_TENSION_ONLY without zero tension:** C_TRUE_1 had zero-tension fraction `0` and `A_2f/A_f` `5.82068e-05`; **no clear 2f above the numerical-control level was produced**.
4. **TRUE_TENSION_ONLY crossing zero:** C_TRUE_2 is a `SYNTHETIC MECHANISM CONTROL`; its zero-tension fraction was `0.44078` and `A_2f/A_f` was `0.0442472`. **The mathematical zero-tension transition has harmonic-generation capability in this control.** This is not evidence that a real PV cable reached zero tension.
5. **1:2 internal-resonance control:** IR0/IR1 use `f2/f1` approximately `2`, while IR2 is `1.6`. Their torsional `A_2f` values are IR0=`0`, IR1=`0.0382397`, and IR2=`0.00487811`; the near-1:2 absolute amplitude change relative to the detuned control is `6.83898` (fraction). **The near-1:2 condition activated/amplified the implemented quadratic modal-transfer response.** Because torsional `A_f` is near zero, its `A_2f/A_f` ratio is ill-conditioned and is not used for this comparison. These are software controls only.
6. **Numerical robustness:** Across baseline step, half step, DOP853, and the 16-cycle window, the normalized spread in `A_2f/A_f` was **0.000539165** (fraction), indicating low sensitivity within only these limited checks.

## Claim boundary

No row confirms a physical cause. In particular, positive-tension softening must not be called cable slackening, and C_TRUE_2 parameters must not be represented as real PV properties.
B0 permits mathematical compression by definition; its negative minimum tension and `T<=0` fraction are not zero-tension state transitions.
