"""Guard the stdlib-only, offline generator contract.

The generator must run as ``python3 scripts/uicons`` with no install step, so
every import in ``tools/uicons`` has to resolve to the standard library or to
the package itself. Heavy third-party rasterizers and CLI frameworks are
banned explicitly, not just absent today.
"""

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools" / "uicons"

# Named explicitly so a future dependency shows up as a deliberate decision,
# not as drift. The stdlib check below already rejects these; the list
# documents the issue's divieto in one place.
BANNED_THIRD_PARTY = ("PIL", "Pillow", "numpy", "click", "pydantic")


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                yield "__relative__"
            elif node.module:
                yield node.module.split(".")[0]


class StdlibOnlyTest(unittest.TestCase):
    def test_generator_imports_are_stdlib_or_intra_package(self):
        allowed = set(sys.stdlib_module_names) | {"__relative__"}
        offenders = {}
        for path in sorted(TOOLS_DIR.glob("*.py")):
            foreign = sorted(
                {name for name in _imported_modules(path) if name not in allowed}
            )
            if foreign:
                offenders[path.name] = foreign
        self.assertEqual(offenders, {})

    def test_heavy_dependencies_are_banned_explicitly(self):
        for path in sorted(TOOLS_DIR.glob("*.py")):
            imported = set(_imported_modules(path))
            for banned in BANNED_THIRD_PARTY:
                self.assertNotIn(
                    banned,
                    imported,
                    f"{path.name} imports banned third-party {banned!r}",
                )


if __name__ == "__main__":
    unittest.main()
