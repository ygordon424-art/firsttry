# Generic Abaqus cable–PV FE prototype

## Status and purpose

This Stage 2B model is a small, parametric, representative cable–panel archetype. It is classified `GENERIC_FE_PROTOTYPE`; every current number is a `GENERIC_PLACEHOLDER_PARAMETER`. It is not the experimental structure, not a 45 m/multi-span/multi-row model, and has not produced an Abaqus result.

The generator uses two laterally separated bilateral `T3D2` cable paths connected to two attachment points on a rigid panel reference body. A point mass and rotary inertia represent the panel at the reference node. This retains vertical translation and, when enabled, rotation about the span direction without solid continuum elements.

## Environment gate

Run:

```powershell
python fe/abaqus/generate_model.py --check-environment
```

The gate reports executable presence, license-variable presence, Python-interface status, and smoke-test status without printing license-server values. An environment variable is not proof of a successful license checkout. If Abaqus is missing, license status remains `UNKNOWN` and no solver output is created.

## Generate the deterministic input framework

```powershell
python fe/abaqus/generate_model.py --config config/fe_generic.yaml --output-dir fe/abaqus/generated
```

This writes an input deck, a manifest, and an environment record. Repeated generation from identical configuration is byte-for-byte deterministic. The deck contains a tiny static placeholder step and an eigenvalue step, but generation does not submit a job.

## Parameters and switches

The YAML exposes span, panel width, panel mass, rotational inertia, cable spacing/area/modulus, nominal pretension, support conditions, damping, and load location. It also exposes future counterfactual switches for `NLGEOM`, pretension, bending–torsion freedom, and tension-only behavior.

- `NLGEOM` maps to the generic static step.
- Pretension, when requested, is represented as a clearly marked initial axial-stress placeholder and must be reviewed against the eventual experimental initialization procedure before execution.
- Bending–torsion freedom controls the panel reference node's span-axis rotation.
- Tension-only FE behavior is deliberately rejected by validation. **`TENSION_ONLY_FE = NOT YET VERIFIED`**. The current cable elements are bilateral trusses; no undocumented material or connector trick is used.

## Output plan

The deck requests displacement/reaction fields and cable stress/strain, plus eigenmodes. The future extraction contract covers:

- panel vertical displacement `u_z(t)`;
- panel torsional/rotational response where available;
- cable axial force `T_i(t)` after its extraction method is verified;
- modal frequencies;
- reactions; and
- relevant internal-force histories in a future dynamic step.

`postprocess_odb.py` currently provides only a schema and an explicit Abaqus `odbAccess` gate. It never creates numerical values when the ODB or Abaqus interface is absent. Future normalized time histories will use `time,z,theta` columns so they can enter `scripts/harmonic_analysis.py` without duplicating spectral logic.

## Required replacement before research use

Replace every placeholder with provenance-controlled experimental geometry, mass/inertia, cable constitutive properties, pretension/initialization, boundary and connection details, damping, load mapping, units, and uncertainty. Then verify element formulation, mesh convergence, equilibrium after pretension, eigenmodes, and measured response before any mechanism or causal claim.
