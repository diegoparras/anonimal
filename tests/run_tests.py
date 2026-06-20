# -*- coding: utf-8 -*-
"""Runner de tests con stdlib (este entorno no tiene pytest instalado).

Uso:  python -m tests.run_tests       (desde la raiz del repo)
Tambien sirve `pytest` cuando este disponible: los tests son funciones test_*.
"""
import importlib
import sys
import traceback

MODULES = ["tests.test_engine", "tests.test_api"]


def main() -> int:
    passed = failed = 0
    failures = []
    for modname in MODULES:
        mod = importlib.import_module(modname)
        for name in sorted(vars(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print(f"  PASS  {modname}.{name}")
            except Exception:  # noqa: BLE001
                failed += 1
                failures.append((f"{modname}.{name}", traceback.format_exc()))
                print(f"  FAIL  {modname}.{name}")

    print(f"\n{passed} passed, {failed} failed")
    for name, tb in failures:
        print(f"\n=== {name} ===\n{tb}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
