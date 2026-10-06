# Stage 1 experimental data requirements

No experimental dataset should enter formal analysis until the following fields are confirmed. Unknown values must remain `UNKNOWN`; they must not be inferred from filenames or test signals.

## Required identification and operating conditions

- **Experiment ID:** unique identifier linking files, run log, instrumentation, and configuration.
- **Wind speed:** value, unit, reference location, averaging definition, and uncertainty.
- **Wind direction:** angle convention, zero direction, sign convention, and uncertainty.
- **Tilt angle:** value, sign convention, reference plane, and unit.
- **Sampling frequency:** nominal and, where possible, verified from timestamps.
- **Duration:** acquisition duration after any discarded startup or shutdown segment.

## Sensors and units

- **Sensor position:** coordinate system, origin, orientation, channel-to-location map, and measurement side.
- **Units:** raw and calibrated units for every channel.
- **Calibration:** calibration date, coefficients, range, resolution, and known filtering.
- **Synchronization:** common clock, trigger method, time offset, and dropped-sample information.

## Scale and structural configuration

- **Scale ratio:** geometric scale and any separate velocity, time, mass, stiffness, or pressure scaling.
- **Initial pretension:** value, unit, application method, tolerance, and measurement method.
- **Structural configuration:** supports, boundary conditions, membrane/panel/cable properties, mass distribution, damping information, and configuration changes between runs.

## Provenance and permitted use

- **Data provenance:** original owner, laboratory, acquisition system, transfer history, checksum, and whether the received file is raw or processed.
- **Publication/source:** full citation, DOI or stable URL, figure/table/run identifier, and relation to any published dataset.
- **Permitted use:** explicitly record one of `validation only`, `new analysis`, or a more restrictive written permission.
- **Processing history:** identify detrending, filtering, resampling, calibration, channel removal, or other transformations already applied.

## Intake rule

Keep the received source immutable. Work from a checksum-identified copy, store audit outputs separately, and never overwrite raw data. Any missing required field must be listed in the audit and resolved or accepted explicitly before a Stage 1 decision gate is passed.
