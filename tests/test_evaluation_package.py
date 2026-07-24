from evaluation.validate_results import validate


def test_compact_confirmatory_results():
    assert validate() == {
        "cases": 100,
        "base_correct": 17,
        "adapter_correct": 39,
        "v2_automated_correct": 59,
        "v2_manual_correct": 71,
        "v2_executable": 85,
        "v2_scorer_false_negatives": 12,
        "adapter_only_correct": 27,
        "base_only_correct": 5,
        "both_correct": 12,
        "both_incorrect": 56,
        "original_v2_both_correct": 28,
        "original_v2_both_incorrect": 30,
        "original_v2_original_only": 11,
        "original_v2_v2_only": 31,
    }
