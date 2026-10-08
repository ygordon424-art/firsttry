# Direction 1 ROM preparation summary

- ROM implemented: **YES**
- Linear baseline passed: **YES**
- Geometric nonlinear switch passed: **YES**
- Tension-only switch passed: **YES**
- Harmonic analysis passed: **YES**
- Formal research conclusion produced: **NO**
- Abaqus started: **NO**
- Experimental validation performed: **NO**

## Scope

The implementation is a 2DOF bending-torsion mechanism-screening surrogate with synthetic, non-physical defaults. It supports linear, smooth geometric-nonlinear, and tension-only/piecewise-stiffness switches, and records the tension surrogate and tangent stiffness. Outputs are isolated beneath `prototype_results/direction1_rom/` and classified `MECHANISM_PROTOTYPE`.

## Verification record

- Clean-HEAD test command: `python -m pytest -q --basetemp=work/pytest -p no:cacheprovider`
- Clean-HEAD test result: **20 passed in 3.89 s**
- Prototype suite ID: `20261008T015634Z-007e40f5`
- Source commit recorded by every prototype case: `e130274b50e129d41c469da9f86fcfa1c1021dee`
- `MODEL_LIN` solver runtime: **0.401 s**
- `MODEL_GEO` solver runtime: **3.091 s**
- `MODEL_TENSION_ONLY` solver runtime: **3.299 s**
- Runtime-limit violation: **NO**
- Final suite error: **NONE**

The prototype produced all required CSV, JSON, and PNG files. The tension-only case recorded both `TAUT` and `LOW_TENSION` surrogate states. Harmonic amplitudes differed among synthetic cases; this is reported only as a signal feature and is not assigned a physical cause.

## Claim boundary

No experimental data, real structural parameters, Fluent data, Abaqus model, parameter fitting, or formal CFD/structural result was used. Signal differences among synthetic cases are software/prototype observations only and do not establish a nonlinear mechanism or paper conclusion.

## Next evidence required

The next step is to obtain provenance-controlled experimental/model parameters and their permitted-use status, then freeze units, mass/inertia, stiffness/coupling, damping, pretension, boundary conditions, modal targets, and validation criteria before any calibrated or full finite-element analysis.
