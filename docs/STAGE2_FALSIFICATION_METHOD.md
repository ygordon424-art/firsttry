# Stage 2 mechanism falsification method

## Purpose

This stage attempts to falsify or narrow the interpretation of the earlier synthetic C3/C4 response. It does not seek a larger 2f peak. All cases are predefined, low-cost software controls classified `STAGE2_MECHANISM_DEVELOPMENT`; no parameter optimization, sweep, Abaqus, CFD, FSI, or experimental fitting is performed.

## Distinct cable-surrogate modes

Let the representative extension be `e = d^T q`, high stiffness be `k_h`, pretension be `T_0`, and the unmodified prediction be `T_raw = T_0 + k_h e`.

### `BILATERAL_LINEAR`

`T = T_raw` and `dT/de = k_h` for all extensions. The element can carry mathematical compression. This is a linear control, not a cable constitutive claim.

### `LOW_TENSION_SOFTENING`

This mode has a positive threshold `T_s`, low stiffness `k_l`, and high stiffness `k_h`. It represents only a low-tension stiffness surrogate. It must never be called slackening.

For `ABRUPT_PIECEWISE`, the high-stiffness line is used above `T_s`; below it, a continuous low-slope line begins at the same transition point. Force is continuous, while tangent stiffness changes abruptly.

For `SMOOTH_TRANSITION`, define the threshold extension `e_s = (T_s - T_0)/k_h`, width `w = W_T/k_h`, `x = (e-e_s)/w`, and `softplus(x) = log(1+exp(x))`. The tension is

`T = T_s + k_l(e-e_s) + (k_h-k_l) w [softplus(x)-log(2)]`.

Its tangent is

`dT/de = k_l + (k_h-k_l) sigmoid(x)`.

Both tension and tangent are continuous; the same pretension, threshold, and high/low stiffness limits are retained for the abrupt/smooth comparison.

### `TRUE_TENSION_ONLY`

This mode has no positive softening threshold. Configuration is rejected unless `low_tension_threshold = 0`. While `T_raw > 0`, normal stiffness is retained: `T=T_raw`, `dT/de=k_h`. If `T_raw <= 0`, the model sets `T=0` and `dT/de=0`. This is a mathematical tension-only control, not evidence that a real PV cable loses tension.

Every applicable case reports minimum/maximum surrogate tension, fraction of samples with `T <= 0`, fraction in the softened state, and the number of recorded state transitions.

## Predefined falsification controls

- `B0`: bilateral linear cable surrogate.
- `B1`: abrupt positive-tension softening, matching the earlier C3 form.
- `B2`: smooth positive-tension softening with the same limiting parameters.
- `C_TRUE_1`: true tension-only with predefined higher synthetic pretension, intended to remain positive.
- `C_TRUE_2`: `SYNTHETIC MECHANISM CONTROL` with predefined lower pretension, intended to cross zero tension.
- `IR0`: linear synthetic system with `f2/f1 ≈ 2`.
- `IR1`: the same near-1:2 system with quadratic bending–torsion coupling.
- `IR2`: the same nonlinear coupling deliberately detuned to `f2/f1 ≈ 1.6`.
- three robustness variants of B1: half maximum step, `DOP853`, and at least 16 analyzed cycles.

The internal-resonance controls use synthetic diagonal M/K matrices and vertical-only forcing. Their purpose is to test software capability for modal transfer, not to represent a measured PV mode pair.

## Interpretation boundary

The report may state that one case exhibited a larger or smaller harmonic amplitude than another, or that results were sensitive to model form/numerical settings. It cannot state that a physical cause has been confirmed. In particular:

- positive-tension softening is not cable slackening;
- a zero-tension software transition is not evidence that the experiment reached zero cable force;
- a near-1:2 synthetic response is not proof of internal resonance in the experiment; and
- numerical robustness does not replace parameter identification or experimental validation.
