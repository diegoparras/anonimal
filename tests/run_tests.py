"""Runner de tests con stdlib (este entorno no tiene pytest instalado).

Uso:  python -m tests.run_tests       (desde la raiz del repo)
Tambien sirve `pytest` cuando este disponible: los tests son funciones test_*.

Convencion de SKIP: una prueba puede devolver un str que empiece con "SKIP"
(p.ej. cuando una herramienta opcional no esta instalada). El runner lo cuenta
como salteado, no como fallo. pytest lo ignora (lo toma como pass).
"""
import importlib
import sys
import traceback

MODULES = ["tests.test_engine", "tests.test_api", "tests.test_privacy", "tests.test_quality"]


def main() -> int:
    passed = skipped = failed = 0
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
                result = fn()
                if isinstance(result, str) and result.startswith("SKIP"):
                    skipped += 1
                    print(f"  SKIP  {modname}.{name}  ({result[6:].strip() or '...'})")
                else:
                    passed += 1
                    print(f"  PASS  {modname}.{name}")
            except Exception:
                failed += 1
                failures.append((f"{modname}.{name}", traceback.format_exc()))
                print(f"  FAIL  {modname}.{name}")

    print(f"\n{passed} passed, {skipped} skipped, {failed} failed")
    for name, tb in failures:
        print(f"\n=== {name} ===\n{tb}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
