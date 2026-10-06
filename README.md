# Rooftop obstacle–PV aerodynamic interference CFD project

Stage 0 infrastructure for the proposed study **“Oblique-Wind-Induced Aerodynamic Interference between Rooftop Service Structures and Photovoltaic Arrays: Load Amplification and Structural Implications.”** The first target journal is the *Journal of Building Engineering (JBE)*.

This repository does not contain claimed CFD findings. It establishes a reproducible workflow and refuses production execution while scientific inputs remain `TBD`.

## 1. Research objective

Quantify how a normalized rectangular rooftop service structure (for example, a plant room or lift overrun) changes oblique-wind loading on a photovoltaic array over a representative flat-roof building, and translate those aerodynamic effects into simplified structural demands.

The intended physical chain is:

`building-edge separation → obstacle wake/shear layer → distorted PV inflow → inter-row interference → Cp/CL/CD/CM → base moment/anchor tension`

## 2. Scientific hypothesis

For selected oblique wind directions and obstacle-to-array spacing ratios, interaction between the building-edge separation region and the rooftop obstacle wake will cause localized PV row-load and support-demand amplification relative to the obstacle-free baseline. The magnitude and affected rows should depend systematically on wind angle and `So/Ho`. This is a hypothesis to test—not a result.

## 3. Repository structure

- `config/`: centralized research parameters, planned case matrix, and an explicit structural-model template.
- `geometry/`: source geometry assets and provenance.
- `validation/`: raw and digitized benchmark evidence with citation requirements.
- `cfd/`: geometry, meshing, boundary-condition, solver, and UDF assets.
- `scripts/`: environment audit, single/batch execution, postprocessing, GCI, structural mapping, smoke testing, and Windows synchronization.
- `postprocessing/`: reusable plotting/report definitions (future stage).
- `results/`: lightweight CSV, metadata, and log summaries. Large solver files are excluded from Git.
- `reports/`: environment and stage summaries.
- `tests/`: minimal unit tests for provenance and numerical interfaces.

The additional `scripts/common.py` and `scripts/smoke_test.py` files centralize provenance and isolate the Stage 0 solver check from production execution.

## 4. Environment requirements

- Python 3.10+ (the inspected host uses Python 3.13.3)
- Git
- Packages in `requirements.txt`
- For real CFD only: a supported ANSYS Fluent installation, a valid license, and enough RAM/scratch storage for the mesh

Create an isolated environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Docker is optional and was not available on the inspected host. No Slurm or PBS client was detected.

## 5. Fluent and PyFluent requirements

PyFluent is a Python client; installing it does not install Fluent or grant a license. A real run requires all three of:

1. a discoverable Fluent executable compatible with the installed PyFluent version;
2. a legitimate Fluent license checkout;
3. a traceable mesh/case built from frozen study parameters.

The inspected environment has PyFluent 0.41.0 but no Fluent executable, so license availability is `UNKNOWN` and no smoke test was run.

## 6. Run the environment check

```powershell
python scripts/check_environment.py --output reports/environment_report.md
```

The check reports license-variable presence only. It never prints license-server addresses, passwords, tokens, or API keys.

## 7. Run the smoke test

On a licensed Fluent host, use a very small, initialized, traceable case (not a production mesh):

```powershell
python scripts/smoke_test.py --case-file path\to\tiny_reference.cas.h5 --processor-count 2 --iterations 5
```

The script launches the real solver in double precision, loads the case/mesh, initializes, iterates, writes `solver_transcript.txt`, `convergence_history.csv`, `smoke_result.csv`, and `smoke_test_status.json`, then closes the session. Record the small case's source and licensing alongside it. A failed launch is recorded as failure; no replacement or synthetic CFD data are generated.

## 8. Run one CFD case

Metadata-only preparation is safe before parameters are frozen:

```powershell
python scripts/run_case.py OBS_S050_A045
```

Real execution is deliberately refused while any research parameter is `TBD`. After configuration, mesh, boundary conditions, and validation are reviewed:

```powershell
python scripts/run_case.py OBS_S050_A045 --execute --case-file path\to\OBS_S050_A045.cas.h5
```

Every run creates `results/runs/<case_id>/<run_id>/metadata.json`, including case ID, Git SHA, date, solver versions, mesh fields, physical/boundary parameters, turbulence/convergence settings, iterations, runtime, core count, and result status. Fields unavailable at a stage remain `null`; they are never invented.

## 9. Future batch execution

Preview selected cases without launching Fluent:

```powershell
python scripts/run_batch.py --all
```

Production execution requires enabling reviewed cases in `cases.yaml`, `--execute`, `--confirm-production`, and a directory containing one prepared `<case_id>.cas.h5` per selected case. Stage 0 must not use those flags. `config/cases.yaml` contains five baselines and fifteen obstacle cases, plus GCI and supplementary reservations; none are enabled or executed now.

## 10. Result structure

Small, reviewable outputs include:

- `metadata.json` for each run;
- solver transcript/log summaries;
- convergence and row-load CSV files;
- small figures and tables.

Large `.cas.h5`, `.dat.h5`, mesh, transient, and ZIP artifacts are ignored by Git. Package them as downloadable CI/HPC artifacts or place them in controlled external storage. On the user's Windows machine, synchronize a result directory or ZIP with:

```powershell
.\scripts\sync_results_windows.ps1 -Source .\result.zip -CaseId OBS_S050_A045 -RunId run-001
```

The default destination is `D:\SWJT\大三\论文\result\<case_id>\<date>\<run_id>`. This repository setup did not claim access to or write to that D: drive.

## 11. Postprocessing and structural mapping

`postprocess.py` validates and normalizes real solver exports into `forces_by_row.csv` with at least:

`case_id, wind_angle, spacing_ratio, row_id, Cd, Cl, Cm, Fx, Fy, Fz, Mx, My, Mz`

If a matching baseline is supplied, it computes `IF_M = Cm_obstacle / Cm_baseline`. If both inputs contain `Mbase`, it also computes `K_M = Mbase_obstacle / Mbase_baseline`. Zero denominators and missing baseline rows are errors.

`structural_mapping.py` implements the future chain `surface pressure → panel resultants → simplified two-column/braced support → M_base, T_anchor, N_brace`. It requires an explicit axis mapping, load height, column spacing, and brace angle (measured from the selected horizontal-force direction); the example remains `TBD` so no final support geometry is implied.

## 12. Reproducibility policy

- All scientific inputs live in version-controlled configuration or traceable case-generation assets.
- Case IDs follow `BASE_A000` and `OBS_S050_A045` conventions.
- Every run records source revision and software/runtime metadata.
- Raw solver artifacts are immutable once accepted; derived outputs identify their source run.
- GCI and validation are required before production claims.
- Random, analytic, or fabricated values must never be presented as Fluent, experimental, validation, or paper results.

Run tests with:

```powershell
python -m pytest -q
```

## 13. Data provenance policy

Published experimental data used for validation must retain full citation and provenance information. Each digitized dataset must identify the publication, DOI or stable URL, figure/table, units, digitization method, operator/date, transformations, and known uncertainty. Never silently alter raw reference data or mix synthetic demonstrations with research results.

## 14. Stage 1 Prep — flexible-PV experimental data intake

Stage 1 Prep adds read-only experimental-data auditing and signal-analysis interfaces while the research direction and source datasets remain unfrozen. It does **not** start Fluent or Abaqus, define a final physical model, or produce paper results.

Install the additional dependencies without changing the frozen Stage 0 dependency set:

```powershell
python -m pip install -r requirements-stage1.txt
```

Audit a received CSV, delimited TXT/DAT, or Excel workbook:

```powershell
python scripts/audit_experimental_data.py path\to\data.csv --output-dir audit_output
```

The audit writes `audit_report.json` and `audit_report.md`, leaves the source untouched, and reports table shape, numeric columns, missing/non-finite values, time-column detection, sampling rate, duration, timestamp duplication, interval uniformity, and IQR-based potential outliers. Unsupported or ambiguous formats fail explicitly.

Analyze a uniformly sampled displacement CSV:

```powershell
python scripts/analyze_displacement.py path\to\displacement.csv --time-column time --displacement-column displacement --displacement-unit mm --output-dir analysis_output
```

Outputs include descriptive statistics, detrended signal, FFT, Welch PSD, dominant-frequency candidates, `f0/2f0/3f0` features, amplitude ratios, CSV summaries, and three PNG plots. A fundamental may be specified with `--fundamental-frequency`; otherwise the largest FFT peak is reported only as a candidate. No nonlinear mechanism is inferred automatically.

`analyze_pressure_array.py` provides modular preparatory interfaces for synchronized pressure channels, Cp conversion, cross-correlation, cross-spectrum, coherence, and phase lag. Formal pressure-array analysis waits for verified channel maps, reference conditions, synchronization, and provenance.

All generated unit-test signals are explicitly labeled `SYNTHETIC_TEST_DATA`, exist only inside temporary test directories, and are forbidden from writing beneath a `results` directory. Synthetic tests verify software behavior only and cannot support a research claim or novelty decision. See `docs/STAGE1_DATA_REQUIREMENTS.md`, `docs/FLEXIBLE_PV_GLOSSARY.md`, and `docs/STAGE1_DECISION_GATE.md` before accepting real data.
