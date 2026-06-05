from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "01_profile_raw_data.py",
    "02_clean_sources.py",
    "03_build_analytics_panel.py",
    "04_build_dimensional_schema.py",
    "05_generate_postgres_sql.py",
    "06_validate_outputs.py",
]


def main() -> None:
    for script in SCRIPTS:
        path = ROOT / "scripts" / script
        print(f"\n==> Ejecutando {script}")
        subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)
    print("\nETL completo finalizado.")


if __name__ == "__main__":
    main()
