# Forcing-versus-Response 2f Protocol

This protocol is a future interpretation aid, not an aerodynamic conclusion. It
requires an explicitly supplied `frequency_reference` (for example a measured
response frequency or an FE modal frequency), a documented analysis window,
and permission appropriate to the dataset's intended use.

## Compare two levels of input

First inspect the local pressure-channel spectra. Then inspect a documented
generalized force, `Q(t) = sum(w_i p_i(t))`. A local tap can contain 2f while
other taps cancel it in `Q`; conversely, spatially aligned components can
reinforce it. The weights must state whether they represent synthetic controls,
tributary area, FE mode shapes, or a measured pressure map.

## Conservative future classification

| Situation | Limited interpretation |
| --- | --- |
| Pressure/generalized force has weak or absent 2f; aeroelastic displacement has strong 2f. | A forcing-only explanation is insufficient; investigate structural or aeroelastic transformation. |
| Pressure has weak 2f; displacement has strong 2f. | Structural or aeroelastic amplification is possible. |
| Pressure/generalized force has strong 2f; displacement has strong 2f. | Do not attribute the response harmonic to structural nonlinear generation without additional counterfactual evidence. |

These comparisons do not prove causality. They need compatible sampling,
calibration, coordinate/mapping metadata, uncertainty checks, and a suitable
counterfactual or structural model before a causal claim is possible.

## Data-permission boundary

Old rigid-model pressure data authorized only for validation must not be
recomputed into new coherence, cross-spectrum, or harmonic findings presented
as experimental Results. If those histories only characterize FE input or
validate loading, label that limited purpose. The Direction 2 non-coherent
loading fallback can be activated only if new/secondary analysis is explicitly
authorized.
