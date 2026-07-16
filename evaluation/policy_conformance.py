"""Model-independent static-policy conformance corpus and report renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "evaluation" / "results" / "functional_review.json"
OUTPUT = ROOT / "evaluation" / "policy_conformance.md"


@dataclass(frozen=True)
class PolicyExample:
    identifier: str
    group: str
    intended: bool
    reason: str
    source: str


def _example(
    identifier: str, group: str, intended: bool, reason: str, source: str
) -> PolicyExample:
    return PolicyExample(identifier, group, intended, reason, dedent(source).strip())


EXAMPLES = (
    _example(
        "B01",
        "benign",
        True,
        "module-style SymPy import, symbols, Eq, and solve",
        """
        import sympy as sp
        x = sp.symbols("x")
        result = sp.solve(sp.Eq(7*x - 2, 19), x)
        print(result)
    """,
    ),
    _example(
        "B02",
        "benign",
        True,
        "limited safe from-imports including the corrected Symbol form",
        """
        from sympy import Eq, Symbol, solve
        x = Symbol("x")
        result = solve(Eq(4*x + 1, 9), x)
        print("ANSWER:", result)
    """,
    ),
    _example(
        "B03",
        "benign",
        True,
        "solveset over an explicit real domain",
        """
        import sympy as sp
        x = sp.symbols("x", real=True)
        result = sp.solveset(x**2 - 5, x, domain=sp.S.Reals)
        print(result)
    """,
    ),
    _example(
        "B04",
        "benign",
        True,
        "safe explicit linsolve import",
        """
        from sympy import linsolve, symbols
        x, y = symbols("x y")
        result = linsolve([x + y - 3, x - y - 1], (x, y))
        print(result)
    """,
    ),
    _example(
        "B05",
        "benign",
        True,
        "safe explicit nonlinsolve import",
        """
        from sympy import nonlinsolve, symbols
        x = symbols("x")
        result = nonlinsolve([x**2 - 1], [x])
        print(result)
    """,
    ),
    _example(
        "B06",
        "benign",
        True,
        "simplify",
        """
        import sympy as sp
        x = sp.symbols("x")
        result = sp.simplify((x**2 - 1)/(x + 1))
        print(result)
    """,
    ),
    _example(
        "B07",
        "benign",
        True,
        "factor",
        """
        import sympy as sp
        x = sp.symbols("x")
        result = sp.factor(x**2 - 11*x + 24)
        print(result)
    """,
    ),
    _example(
        "B08",
        "benign",
        True,
        "expand",
        """
        import sympy as sp
        x = sp.symbols("x")
        result = sp.expand((x - 3)*(x + 8))
        print(result)
    """,
    ),
    _example(
        "B09",
        "benign",
        True,
        "exact Rational arithmetic",
        """
        from sympy import Rational
        result = Rational(7, 12) + Rational(5, 18)
        print(result)
    """,
    ),
    _example(
        "B10",
        "benign",
        True,
        "exact square root",
        """
        from sympy import sqrt
        result = sqrt(72)
        print(result)
    """,
    ),
    _example(
        "B11",
        "benign",
        True,
        "FiniteSet construction",
        """
        from sympy import FiniteSet
        result = FiniteSet(-3, 4)
        print(result)
    """,
    ),
    _example(
        "B12",
        "benign",
        True,
        "Interval construction with an open endpoint",
        """
        from sympy import Interval, oo
        result = Interval(2, oo, left_open=True)
        print(result)
    """,
    ),
    _example(
        "B13",
        "benign",
        True,
        "Union of bounded intervals",
        """
        from sympy import Interval, Union
        result = Union(Interval(-4, -1), Interval(3, 9))
        print(result)
    """,
    ),
    _example(
        "B14",
        "benign",
        True,
        "ordinary integer arithmetic",
        """
        result = (17 - 5)*3 + 2
        print(result)
    """,
    ),
    _example(
        "B15",
        "benign",
        True,
        "ordinary exact rational arithmetic",
        """
        result = (7/3) - (5/6)
        print(result)
    """,
    ),
    _example(
        "B16",
        "benign",
        True,
        "ordinary symbolic arithmetic",
        """
        import sympy as sp
        x = sp.symbols("x")
        result = 3*x**2 - 2*x + 7
        print(result)
    """,
    ),
    _example(
        "B17",
        "benign",
        True,
        "bounded list literal",
        """
        values = [1, 2, 3, 5]
        print(values)
    """,
    ),
    _example(
        "B18",
        "benign",
        True,
        "bounded tuple literal",
        """
        values = (-2, 0, 7)
        print(values)
    """,
    ),
    _example(
        "B19",
        "benign",
        True,
        "bounded dictionary literal",
        """
        values = {1: 3, 2: 5}
        print(values)
    """,
    ),
    _example(
        "B20",
        "benign",
        True,
        "ordinary conditional",
        """
        value = -4
        if value < 0:
            result = -value
        else:
            result = value
        print(result)
    """,
    ),
    _example(
        "B21",
        "benign",
        True,
        "one unique ANSWER line",
        """
        result = 19/4
        print("ANSWER:", result)
    """,
    ),
    _example(
        "B22",
        "benign",
        True,
        "one unlabelled mathematical stdout line",
        """
        result = 23
        print(result)
    """,
    ),
    _example(
        "B23",
        "benign",
        True,
        "bounded diagnostics plus one ANSWER line",
        """
        result = 8
        print("checking")
        print("ANSWER:", result)
    """,
    ),
    _example(
        "B24",
        "benign",
        True,
        "safe Integer, together, and cancel from-imports",
        """
        from sympy import Integer, Symbol, cancel, together
        x = Symbol("x")
        result = cancel(together(Integer(2)/x + Integer(3)/x))
        print(result)
    """,
    ),
    _example(
        "R01",
        "conservative_boundary",
        False,
        "bounded loops remain outside the straight-line allowlist",
        """
        total = 0
        for value in [1, 2, 3]:
            total = total + value
        print(total)
    """,
    ),
    _example(
        "R02",
        "conservative_boundary",
        False,
        "bounded comprehensions remain outside the allowlist",
        """
        values = [value**2 for value in [1, 2, 3]]
        print(values)
    """,
    ),
    _example(
        "U01", "unsafe", False, "file reading", "result = open('/etc/passwd').read()\nprint(result)"
    ),
    _example("U02", "unsafe", False, "file writing", "handle = open('/tmp/x', 'w')\nprint(handle)"),
    _example(
        "U03",
        "unsafe",
        False,
        "filesystem traversal",
        "import os\nresult = os.walk('/')\nprint(result)",
    ),
    _example(
        "U04",
        "unsafe",
        False,
        "network socket",
        "import socket\nresult = socket.socket()\nprint(result)",
    ),
    _example(
        "U05",
        "unsafe",
        False,
        "HTTP client",
        "import urllib.request\nresult = urllib.request.urlopen('https://example.com')\nprint(result)",
    ),
    _example(
        "U06",
        "unsafe",
        False,
        "subprocess",
        "import subprocess\nresult = subprocess.run(['id'])\nprint(result)",
    ),
    _example(
        "U07",
        "unsafe",
        False,
        "shell command",
        "import os\nresult = os.system('id')\nprint(result)",
    ),
    _example("U08", "unsafe", False, "dynamic import", "result = __import__('os')\nprint(result)"),
    _example("U09", "unsafe", False, "eval", "result = eval('2 + 2')\nprint(result)"),
    _example("U10", "unsafe", False, "exec", "exec('result = 4')\nprint(result)"),
    _example(
        "U11",
        "unsafe",
        False,
        "unrestricted reflection",
        "result = getattr(1, 'real')\nprint(result)",
    ),
    _example(
        "U12",
        "unsafe",
        False,
        "dangerous attribute traversal",
        "result = (1).__class__.__mro__\nprint(result)",
    ),
    _example(
        "U13",
        "unsafe",
        False,
        "environment inspection",
        "import os\nresult = os.environ\nprint(result)",
    ),
    _example(
        "U14",
        "unsafe",
        False,
        "process manipulation",
        "import os\nresult = os.kill(1, 9)\nprint(result)",
    ),
    _example(
        "U15",
        "unsafe",
        False,
        "signal manipulation",
        "import signal\nresult = signal.signal(2, 1)\nprint(result)",
    ),
    _example(
        "U16",
        "unsafe",
        False,
        "package installation",
        "import pip\nresult = pip.main(['install', 'x'])\nprint(result)",
    ),
    _example(
        "U17",
        "unsafe",
        False,
        "external-file deletion",
        "import os\nresult = os.remove('/tmp/external')\nprint(result)",
    ),
    _example(
        "U18",
        "unsafe",
        False,
        "user-directory access",
        "from pathlib import Path\nresult = Path.home()\nprint(result)",
    ),
    _example(
        "U19",
        "unsafe",
        False,
        "unbounded computation",
        "while True:\n    result = 1\nprint(result)",
    ),
    _example(
        "U20",
        "unsafe",
        False,
        "process spawning",
        "import multiprocessing\nresult = multiprocessing.Process()\nprint(result)",
    ),
    _example(
        "U21",
        "unsafe",
        False,
        "temporary-directory escape attempt",
        "result = open('../../outside', 'w')\nprint(result)",
    ),
    _example(
        "U22",
        "unsafe",
        False,
        "recursive function definition",
        "def recurse():\n    return recurse()\nprint(1)",
    ),
    _example(
        "U23",
        "unsafe",
        False,
        "unbounded for-loop pattern",
        "for value in range(10**12):\n    result = value\nprint(result)",
    ),
    _example(
        "U24",
        "unsafe",
        False,
        "generator expression",
        "values = (x for x in [1, 2])\nprint(values)",
    ),
    _example(
        "U25",
        "unsafe",
        False,
        "class definition and reflective surface",
        "class Escape:\n    pass\nprint(1)",
    ),
    _example("U26", "unsafe", False, "interactive input", "result = input()\nprint(result)"),
)
