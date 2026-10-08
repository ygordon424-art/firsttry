# Direction 1 reduced-order mechanism prototype

## Purpose and status

This two-degree-of-freedom (2DOF) model is a **mechanism-screening surrogate**. It exists to verify a reproducible numerical pathway for comparing linear, smooth geometric-nonlinear, and low-tension piecewise responses before experimental parameters are available. It is not a validated full flexible-PV model, not an Abaqus replacement, and not a source of formal research conclusions.

All values in `config/rom_config.yaml` are labeled `SYNTHETIC / NON-PHYSICAL DEFAULT`. They have no asserted relationship to a particular prototype, wind-tunnel model, cable-net PV system, or 45 m structure.

## Governing equations

The generalized coordinates are

`q = [z, theta]^T`,

where `z` is a representative bending coordinate and `theta` is a representative torsional coordinate. The solver integrates

`M q_ddot + C q_dot + F_int(q) = F_ext(t)`

with `scipy.integrate.solve_ivp`. The mass, damping, stiffness, nonlinear coefficients, initial conditions, forcing, output interval, and duration come from YAML configuration. A direct damping matrix can be supplied; otherwise the configured damping ratio is converted to a two-mode Rayleigh damping matrix.

## Switchable internal-force models

### `MODEL_LIN`

`F_int = K q`. This is the linear comparison baseline.

### `MODEL_GEO`

The linear force is augmented with configurable smooth quadratic/cubic bending-torsion terms. The terms are deliberately generic and are not calibrated to a real panel, membrane, support, or cable system.

### `MODEL_TENSION_ONLY`

A representative extension is projected from `q`. With `tension_only: false`, the element remains bidirectional and linearly stiff, and no piecewise branch is used. With `tension_only: true`, its tangent stiffness changes when the configured tension surrogate enters the low-tension range; a zero-tension state is also available. This is a tension-only/piecewise-stiffness **surrogate**, not a real cable finite-element formulation.

The model records `T_surrogate(t)`, `K_tangent(t)`, and the active stiffness-state label. A changed second-harmonic amplitude may be reported as a signal feature. It must not be described as proof that cable slackening, structural nonlinearity, or another physical mechanism caused that change.

## Synthetic forcing and minimum cases

The runner supports:

- deterministic single-frequency harmonic forcing; and
- deterministic broadband synthetic forcing represented by a configured sum of sinusoids.

The minimum suite runs only the following three cases with the same forcing and initial conditions:

- A: `MODEL_LIN`;
- B: `MODEL_GEO`;
- C: `MODEL_TENSION_ONLY` with the piecewise switch enabled.

There is no parameter sweep, Monte Carlo study, model fitting, Fluent run, Abaqus run, full-scale model, or long-duration production analysis. Each solve has a hard five-minute maximum, and the defaults are intended to finish in seconds.

## Outputs and signal processing

Each independent run is written beneath `prototype_results/direction1_rom/<run_id>/<model>/`, never beneath formal `results/`. It contains metadata, time histories, FFT/Welch spectra, harmonic ratios, and diagnostic plots. Every output is classified `MECHANISM_PROTOTYPE` and labeled as synthetic.

FFT, Welch PSD, and `f0/2f0/3f0` extraction reuse `scripts/harmonic_analysis.py`. The software reports amplitudes and `A_2f/A_f`, `A_3f/A_f`. Absence of a resolvable harmonic must be retained rather than tuned away.

Run the suite with:

```powershell
python scripts/nonlinear_rom.py --config config/rom_config.yaml
```

## What the prototype can and cannot say

It can show that the software switches constitutive branches, integrates the specified equations, produces traceable outputs, and measures spectral features consistently. It can also support future planning about which measured quantities and parameters are necessary.

It cannot establish the governing physical mechanism, validate a flexible PV structure, quantify real wind response, demonstrate novelty, select a paper conclusion, or infer full-scale safety.

## Replacement with real data and Abaqus

Before research use, replace synthetic values with provenance-controlled measurements or identified properties: mass/inertia, stiffness and coupling, damping, pretension, low-tension behavior, boundary conditions, modal properties, load mapping, units, scale ratio, and uncertainty. Permission constraints in `docs/STAGE1_DECISION_GATE.md` still apply.

If the direction passes its decision gate, a reviewed Abaqus or other nonlinear finite-element model may replace this surrogate. That later model requires geometry, material/section definitions, connections, pretension initialization, mesh convergence, solver verification, and experimental validation. None of those steps is performed here.
