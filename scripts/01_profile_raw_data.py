from __future__ import annotations

import json
from pathlib import Path

from etl_common import (
    DATASETS_DIR,
    DOCUMENTACION_DIR,
    RAW_PROFILE_PATH,
    ROOT,
    count_csv_rows,
    dedupe_columns,
    detect_encoding,
    detect_input_files,
    ensure_dirs,
    read_csv_header,
    update_metadata,
)


def profile_csv(path: Path) -> dict:
    header = read_csv_header(path)
    normalized_columns = dedupe_columns(header)
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "encoding_detected": detect_encoding(path),
        "row_count": count_csv_rows(path),
        "column_count": len(header),
        "columns_original": header,
        "columns_normalized": normalized_columns,
    }


def main() -> None:
    ensure_dirs()
    detected_files = detect_input_files()

    csv_profiles = {
        dataset: profile_csv(ROOT / rel_path)
        for dataset, rel_path in sorted(detected_files.items())
    }

    documentation_files = [
        str(path.relative_to(ROOT))
        for path in sorted(DOCUMENTACION_DIR.glob("*"))
        if path.is_file()
    ]

    raw_profile = {
        "datasets_dir": str(DATASETS_DIR.relative_to(ROOT)),
        "detected_files": detected_files,
        "csv_profiles": csv_profiles,
        "documentation_files": documentation_files,
    }
    RAW_PROFILE_PATH.write_text(
        json.dumps(raw_profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    update_metadata(
        detected_files=detected_files,
        raw_profiles=csv_profiles,
        documentation_files=documentation_files,
    )
    print("Perfilado inicial completado.")


if __name__ == "__main__":
    main()
