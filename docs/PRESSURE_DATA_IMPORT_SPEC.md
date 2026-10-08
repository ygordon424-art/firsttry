# Pressure Data Import Specification

This specification prepares a future import only. It does not assume a teacher's file format or authorise analysis of a supplied dataset.

## Required information

Provide or document these fields with every future pressure dataset:

- `time`
- `channel_id`
- `x`, `y`, `z` coordinates
- `pressure`
- `reference_pressure`
- `reference_velocity`
- `air_density`
- `wind_speed`
- `wind_direction`
- `tilt_angle`
- `sampling_frequency`
- `units`

Where known, also record `sensor_tap_area` or `tributary_area`. For a future
generalized-force calculation, a channel map may optionally include
`mode_weight` and `tributary_area`; these are user-supplied mapping inputs, not
quantities this repository will infer.

Also retain calibration, coordinate-system definition, channel/tap layout, acquisition synchronisation, filtering, missing-data convention, scale ratio (if applicable), and a permission statement.

## One file per channel

Keep the raw files unchanged. Create a separate `channel_map.csv` with one row per channel, for example:

```text
channel_id,source_file,source_pressure_column,x,y,z,pressure_unit,tributary_area,mode_weight
P001,P001.csv,pressure_Pa,0.00,0.00,0.00,Pa,,
P002,P002.csv,pressure_Pa,0.25,0.00,0.00,Pa,,
```

Each source file must identify its time column and confirm the sampling clock is synchronized with the other files. Store common test metadata in a companion metadata file rather than copying it inconsistently into every row.

## One large matrix

Keep the matrix unchanged and provide a `channel_map.csv` that maps each pressure column name to its physical channel and coordinate, for example:

```text
channel_id,matrix_column,x,y,z,pressure_unit,tributary_area,mode_weight
P001,tap_001_Pa,0.00,0.00,0.00,Pa,,
P002,tap_002_Pa,0.25,0.00,0.00,Pa,,
```

Identify the matrix time column separately. Do not infer coordinates from column order or invent missing wind, reference, or unit metadata.

## Permission boundary

If a teacher's data are approved only for validation, do **not** recalculate the prior 1728-point pressure data into coherence results and present them as original paper findings. Validation-only use remains validation-only.

If cross-spectrum, coherence, phase lag, or spatial-correlation findings are intended as paper Results, obtain the teacher's explicit permission for new or secondary analysis first. Record that permission with the dataset before analysis.

If pressure histories are used only to characterize a finite-element input or
validate loading, label that restricted role clearly. It is not permission to
present a newly calculated harmonic, coherence, or cross-spectrum result as a
new experimental finding.
