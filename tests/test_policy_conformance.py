from evaluation.policy_conformance import EXAMPLES
from codellama_algebra.confirmatory_validation import validate_confirmatory_code


def test_all_policy_examples_match_prespecified_results():
    for example in EXAMPLES:
        result = validate_confirmatory_code(example.source)
        assert result.valid is example.intended, (example.identifier, result)


def test_policy_suite_covers_required_surfaces():
    reasons = " ".join(example.reason for example in EXAMPLES)
    required = (
        "file reading",
        "file writing",
        "filesystem traversal",
        "network socket",
        "HTTP client",
        "subprocess",
        "shell command",
        "dynamic import",
        "eval",
        "exec",
        "reflection",
        "attribute traversal",
        "environment inspection",
        "process manipulation",
        "signal manipulation",
        "package installation",
        "external-file deletion",
        "user-directory access",
        "unbounded computation",
        "process spawning",
        "escape attempt",
    )
    for phrase in required:
        assert phrase in reasons
