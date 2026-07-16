from evaluation.validate_results import validate


def test_compact_confirmatory_results():
    assert validate() == {
        "cases": 100,
        "base_correct": 17,
        "adapter_correct": 39,
        "adapter_only_correct": 27,
        "base_only_correct": 5,
        "both_correct": 12,
        "both_incorrect": 56,
    }
