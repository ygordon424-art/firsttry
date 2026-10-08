# Direction 2: Minimal Spatial-Coherence Prototype

## What this prototype does

This is a small code check for a possible future research direction: whether wind pressure at different points is perfectly synchronized. It uses only eight artificial signals, marked `SYNTHETIC_TEST_DATA`, and one artificial modal degree of freedom. It produces no evidence about a real flexible photovoltaic structure.

The existing `analyze_pressure_array.py` pairwise functions are reused for correlation, cross-spectrum, magnitude-squared coherence, and phase lag. The new prototype only combines those pairwise results across a few channels and relates them to synthetic point coordinates.

## Plain-language terms

- **Correlation** asks whether two signals rise and fall together after allowing one signal to be shifted in time. A value near one means a strong similar pattern; a low value means the patterns are weakly related.
- **Cross-spectrum** asks the same relationship separately at different fluctuation frequencies.
- **Coherence** is a frequency-by-frequency measure from zero to one. Near one means the two signals have a reliable relationship at that frequency; near zero means little reliable relationship.
- **Phase lag** describes where one repeating signal occurs within a cycle relative to another. It can be reported as an angle or an equivalent time shift at a stated frequency.

Points on a surface need not experience wind pressure at the same instant. Gusts travel, separate flow regions can develop, and turbulence changes across space. Therefore, a fully coherent assumption can make the forces from many points add more strongly than a partially coherent representation. The small response demo illustrates this computational possibility only: pressure spatial coherence → generalized modal force → linear oscillator response.

## Deliberate limits

This is not a PV structural model, is not a calibrated modal model, and does not analyse real pressure data. It has no 1728-channel simulation, Monte Carlo run, Fluent case, Abaqus case, parameter scan, or paper result. The output is limited to `prototype_results/direction2_coherence/`, and metadata set `data_classification = SYNTHETIC_TEST_DATA` and `research_evidence = false`.

Formal work needs synchronized real time histories, mapped coordinates, units and reference conditions, structural/modal properties, and explicit permission for any secondary analysis. See [PRESSURE_DATA_IMPORT_SPEC.md](PRESSURE_DATA_IMPORT_SPEC.md) for the import and permission requirements.
