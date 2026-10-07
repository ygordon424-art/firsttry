# Stage 1 decision gate

Stage 1 remains preparatory. Neither direction is selected until provenance, metadata, and signal quality are adequate. Synthetic tests verify software only and cannot satisfy a GO criterion.

## Direction 1 — nonlinear structural mechanism / harmonic generation

### Data required

- Calibrated displacement time histories for repeated wind speeds and configurations.
- Verified timestamps, sampling frequency, duration, units, sensor position, and synchronization.
- Structural configuration, dimensions, mass, stiffness, boundary conditions, damping evidence, and initial pretension.
- Sufficient amplitude resolution and record length to distinguish stable harmonics from leakage and noise.
- Preferably simultaneous pressure or force measurements for load–response comparison.
- Provenance and a permission statement matched to the intended role of the data. `Permission for new analysis` is required only if the existing experimental time histories will themselves be reanalyzed and presented as new experimental findings.

### GO only if

- Reproducible components near `f0`, `2f0`, or `3f0` survive data-quality, windowing, leakage, and repeatability checks.
- Fundamental-frequency selection is supported by structural/modal information or an explicitly justified signal criterion.
- Structural parameters are adequate to formulate and validate a bounded mechanistic model.
- Metadata and permitted use support the intended role of the experimental data.
- Data marked `validation only` may support a GO decision when they are used solely to validate a newly developed nonlinear finite-element model and the paper's original results come from new numerical mechanism analysis.
- If the existing displacement time histories will be reanalyzed and reported as new experimental findings, explicit `permission for new analysis` is available.

### NO-GO if

- Displacement records, sampling metadata, units, pretension, or structural configuration are missing.
- Apparent harmonics cannot be separated from sensor artifacts, clipping, spectral leakage, or nonstationary operating conditions.
- Only a single unrepeatable trace is available for the proposed validation or mechanism assessment.
- The intended use exceeds the granted permission. `Validation only` is not by itself a NO-GO when the experimental data remain validation evidence and a separate original numerical/model contribution is present.

## Direction 2 — 3D non-coherent wind loading / structural response error

### Data required

- Synchronized multi-point pressure time histories with a complete tap/channel coordinate map.
- Reference static and dynamic pressure, wind speed, wind direction, tilt angle, units, and calibration.
- Adequate spatial coverage and duration for correlation, cross-spectrum, coherence, and phase estimates.
- Structural model or modal properties sufficient to map distributed pressure to response.
- Repeated or comparable cases that support uncertainty assessment.
- Provenance and a clearly defined permission statement. Recalculation of spatial correlation, cross-spectrum, coherence, phase lag, or related quantities from existing pressure time histories as original paper results requires explicit `permission for new analysis`.

### GO only if

- Channel synchronization and spatial coordinates are verified.
- Pressure normalization and reference conditions are unambiguous.
- Coherence/cross-spectrum estimates are statistically usable over the response-relevant frequency range.
- A defensible structural-response mapping can compare spatially coherent and non-coherent load representations.
- Explicit `permission for new analysis` is available if existing pressure histories are reprocessed to produce original correlation, cross-spectrum, coherence, phase-lag, or similar findings.
- If the existing pressure data are restricted to validation, a separate new dataset, model, method, or numerical contribution provides the paper's original contribution.

### NO-GO if

- Pressure channels are not synchronized or the tap map is missing.
- Reference pressure, dynamic pressure, units, sampling rate, or wind metadata are unknown.
- Spatial coverage is too sparse for the proposed comparison.
- No structural properties are available to quantify response error.
- The intended reanalysis of existing pressure histories is not covered by the granted permission.
- Existing pressure data are limited to validation and no independent original data, model, method, or numerical contribution is available.

## Decision record

At the gate, record the chosen direction, dataset IDs, unresolved limitations, evidence supporting GO/NO-GO, reviewer, and date. Signal features must not be relabeled as mechanisms without independent physical evidence.
