# Stage 2 main mechanism/FE status

- Research protocol frozen: **YES**
- Single-frequency no-2f forcing control implemented: **YES**
- Linear negative control passed: **YES**
- Injected-2f detection control passed: **YES**
- Quadratic/asymmetric mechanism implemented: **YES**
- Cubic mechanism separately implemented: **YES**
- Tension-only surrogate retained: **YES**
- Bending-torsion mechanism switch available: **YES**
- Formal causal conclusion produced: **NO**
- Abaqus available: **NO**
- Abaqus license available: **UNKNOWN**
- Generic FE generator implemented: **YES**
- Actual experiment FE model built: **NO**
- Experimental validation performed: **NO**
- CFD started: **NO**
- FSI started: **NO**
- All tests passed: **YES**
- Runtime of mechanism suite: **41.060 s**

Clean-HEAD verification for source commit `c56aa30`: **28 passed in 11.67 s**. The test copy was exported from the commit so unrelated uncommitted workspace files could not affect the result.

## Mechanism-screening record

The fixed synthetic suite `20261008T035926Z-72140356` used `frequency_reference: FORCING`, a 0.8 Hz single-frequency input for C0–C5, a 50% startup discard, an eight-cycle Hann-windowed analysis interval, and no input 2f. PC1 alone contained a small injected 2f component and served only as `INPUT_2F_DETECTION`.

The linear negative-control `A_2f/A_f` was approximately `6.92e-05`. The cubic-only and bending–torsion-coupling cases remained near that level. The quadratic-only case was approximately `1.24e-04`. The tension-only/piecewise and combined quadratic/piecewise cases were approximately `2.73e-02` and recorded stiffness-state transitions. Their surrogate tension remained positive; this is not evidence of cable slackening. PC1 detected externally supplied 2f, but its response amplitude ratio is shaped by the synthetic transfer function and must not be interpreted as the input amplitude fraction.

No parameter was retuned after seeing these results. The complete non-causal table is in `reports/STAGE2_ROM_MECHANISM_SCREENING.md`.

## Abaqus environment result

No Abaqus executable or common versioned command was found. No Abaqus/LM license environment variable was present. Without an executable, a license checkout and Abaqus Python interface cannot be tested, so license availability remains `UNKNOWN` and the smoke test is `NOT RUN`. No Abaqus result was fabricated.

The deterministic generator produced a tiny bilateral `T3D2` two-path cable/rigid-panel input framework classified `GENERIC_FE_PROTOTYPE`. `TENSION_ONLY_FE = NOT YET VERIFIED`; requesting that switch is rejected. The deck has not been submitted.

## Known limitations

- All ROM coefficients and FE dimensions/properties are synthetic placeholders.
- The ROM is 2DOF and has no aerodynamic feedback, distributed cable modes, connection detail, or validated 1:2 modal relationship.
- Harmonic thresholds are software-control tolerances, not statistical significance criteria.
- Startup suppression, Hann windowing, integer-cycle truncation, and bin-error reporting reduce common spectral artifacts but do not establish physical causality.
- The piecewise surrogate records low-tension/taut state changes; it is not a verified cable constitutive model.
- The generic Abaqus deck has not passed solver syntax, equilibrium, eigenvalue, mesh, pretension, or experimental validation checks.

## Exact experimental parameters still needed

- geometry, cable path, panel/support topology, connection and boundary details;
- panel mass, center of mass, rotational inertia, and mass distribution;
- cable area, modulus/constitutive law, initial pretension, pretension procedure, and evidence for any loss of tension;
- linear and nonlinear stiffness/coupling data, natural frequencies, mode shapes, and damping;
- forcing definition, load distribution/location, wind speed/direction, and synchronization;
- displacement/rotation/pressure channel positions, units, sampling frequency, duration, calibration, and uncertainty;
- scale ratio, structural configuration, experiment ID, provenance, publication/source, and permitted use;
- validated criteria for comparing modeled and measured `A_f`, `A_2f`, `A_3f`, phase, and modal response.

## Exact next step

Review the frozen protocol and synthetic screening without treating C3/C4 as a physical conclusion. Then obtain the provenance-controlled experimental/model parameters above and a licensed Abaqus environment. Verify the generic deck with a sub-five-minute syntax/eigenvalue/pretension smoke test before building or calibrating the actual experimental FE model.
