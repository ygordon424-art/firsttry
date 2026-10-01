from scripts.common import find_case, metadata_template


def test_case_lookup_and_metadata_fields():
    cases = {"cases": [{"case_id": "OBS_S050_A045", "wind_angle": 45}]}
    case = find_case(cases, "OBS_S050_A045")
    metadata = metadata_template(case, {"solver": {}}, status="PREPARED")
    required = {
        "case_id",
        "git_commit_sha",
        "date_utc",
        "solver_version",
        "mesh_cells",
        "mesh_quality",
        "physical_parameters",
        "boundary_conditions",
        "turbulence_model",
        "convergence_criteria",
        "actual_iterations",
        "wall_clock_runtime_seconds",
        "cpu_core_count",
        "result_status",
    }
    assert required.issubset(metadata)

