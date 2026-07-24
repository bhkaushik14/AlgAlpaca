from pathlib import Path

DOCS = [
    Path("README.md"),
    Path("MODEL_CARD.md"),
    Path("evaluation/README.md"),
    Path("evaluation/comparison.md"),
    *Path("docs").glob("*.md"),
]
TEXT = "\n".join(p.read_text() for p in DOCS)


def test_metrics_and_paired_counts():
    for value in ["17/100", "39/100", "59/100", "71/100"]:
        assert value in TEXT
    for value in ["adapter-only 27", "base-only 5", "both correct 12", "both incorrect 56"]:
        assert value in TEXT
    for value in ["original only 11", "v2 only 31", "both correct 28", "both incorrect 30"]:
        assert value in TEXT


def test_no_private_or_prohibited_claims():
    lowered = TEXT.lower()
    assert "/home/" not in TEXT and "bhavya" not in lowered
    assert "statistically significant" not in lowered and "production ready" not in lowered
    assert "adapter is a standalone 7b model" not in lowered
    assert "mit applies only" in lowered or "mit covers newly" in lowered


def test_relative_markdown_links_resolve():
    import re

    for p in DOCS:
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", p.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (p.parent / target.split("#", 1)[0]).resolve().exists(), (p, target)
