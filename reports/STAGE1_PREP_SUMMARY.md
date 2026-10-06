# Stage 1 Prep summary

Date: 2026-10-06 (Asia/Shanghai)

Branch: `stage1-prep`

Base: Stage 0 commit `03ec3e830a1d049380ff32a642d81efe6ae3b5e1`

## Scope completed

- Added a read-only audit tool for CSV, delimited TXT/DAT, and Excel tables.
- Added automatic column inventory, numeric-column identification, missing/non-finite value counts, source checksum, time-column detection, sampling-frequency and duration estimates, duplicate timestamp checks, interval-uniformity checks, and IQR-based potential-outlier flags.
- Added displacement statistics, linear detrending, one-sided FFT, Welch PSD, dominant-frequency candidates, and traceable CSV/PNG outputs.
- Added a standalone `f0`, `2f0`, `3f0` feature module with manual or candidate fundamental selection and `A_2f/A_f`, `A_3f/A_f` ratios.
- Added modular pressure-array interfaces for synchronized channels, Cp conversion, cross-correlation, cross-spectrum, coherence, and phase lag.
- Added experimental-data requirements, an undergraduate glossary, and two explicit Stage 1 decision gates.
- Added separate Stage 1 dependencies so the frozen Stage 0 requirements remain unchanged.

## Scientific status

- Real experimental data received: **NO**
- Formal experimental analysis performed: **NO**
- Fluent started: **NO**
- Abaqus model or solve started: **NO**
- Final physical model assumed: **NO**
- Research direction selected: **NO**
- Synthetic signal used as research evidence: **NO**

Synthetic sine waves are used only in unit tests and carry the `SYNTHETIC_TEST_DATA` label. Tests write only to pytest temporary directories; the displacement writer explicitly rejects synthetic output paths beneath any `results` directory. No synthetic values are presented as experimental, validation, CFD, FEA, or paper results.

## Candidate directions retained

1. Nonlinear structural mechanism / harmonic generation.
2. 3D non-coherent wind loading / structural response error.

Neither direction is GO. `docs/STAGE1_DECISION_GATE.md` lists the required data and GO/NO-GO conditions. Spectral harmonics are reported as signal features only and do not establish a nonlinear mechanism.

## Verification

- Full test suite: **13 passed**.
- Excel round-trip test executed with `openpyxl 3.1.5`.
- Python compilation check: **passed**.
- Stage 0 case matrix modified: **NO**.
- Stage 0 Fluent execution performed: **NO**.

## Exact next step

Wait for the original flexible-PV displacement and/or synchronized pressure datasets plus their complete metadata and permission statement. On receipt, preserve the original files, compute checksums, run `audit_experimental_data.py`, resolve missing metadata, and then apply the decision gate before any formal interpretation, Abaqus model, or CFD/FSI campaign.
