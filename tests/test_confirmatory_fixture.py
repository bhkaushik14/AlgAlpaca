from evaluation.validate_confirmatory import DESIGN_MATRIX, load_cases, validate_cases


def test_design_matrix_has_ten_planned_structures_per_category():
    assert len(DESIGN_MATRIX) == 10
    assert all(len(rows) == 10 for rows in DESIGN_MATRIX.values())


def test_confirmatory_fixture_passes_full_validation():
    summary = validate_cases(load_cases())
    assert summary["total"] == 100
    assert summary["manual_derivations_verified"] == 100
    assert summary["independent_machine_verifications"] == 100
    assert summary["scorer_compatibility"] == 100
    assert summary["policy_method_compatibility"] == 100
