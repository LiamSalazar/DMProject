from __future__ import annotations

import numpy as np
import pandas as pd

from etl_common import (
    ANALYTICS_DIR,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_YEAR,
    INFRA_USE_RECOMMENDED,
    REPORTS_DIR,
    SOCIAL_FEATURES,
    SOCIAL_VARIABLES,
    clean_string_columns,
    ensure_dirs,
    load_mmip_dictionary,
    load_metadata,
    read_output_csv,
    update_metadata,
    write_csv,
)


TARGET = "target_robos_patrimoniales_total"
FGJ_CONTROL_COLUMNS = [
    "total_delitos_fgj",
    "total_robos_patrimoniales",
    "robo_a_transeunte",
    "robo_a_negocio",
    "robo_a_casa_habitacion",
    "robo_de_vehiculo",
    "robo_de_accesorios_auto",
    "robo_del_interior_de_vehiculo",
]
MODEL_CONTROL_COLUMNS = [
    "total_delitos_fgj",
    "n_registros_sociales",
    "factor_sum",
    "infraestructura_actualizacion_anio",
    "infraestructura_es_snapshot",
]


def _data_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def build_feature_catalog(modeling_panel: pd.DataFrame) -> pd.DataFrame:
    dictionary = load_mmip_dictionary()
    rows = []
    for col in modeling_panel.columns:
        if col == TARGET:
            role = "target"
            source = "fgj"
            description = "Total anual de robos patrimoniales clasificados para la alcaldia."
            leakage = "target"
            recommended = False
            temporal = "annual"
        elif col in {"alcaldia_id", "tiempo_id", "alcaldia_key", "alcaldia_nombre", "anio"}:
            role = "id"
            source = "etl"
            description = "Identificador o llave de la unidad alcaldia-anio."
            leakage = "none"
            recommended = False
            temporal = "metadata" if col != "anio" else "annual"
        elif col in SOCIAL_FEATURES:
            raw = col.replace("_wmean", "")
            role = "feature"
            source = "pobreza_mmip"
            description = dictionary.get(raw) or f"Promedio ponderado por factor de {raw}."
            leakage = "low"
            recommended = True
            temporal = "annual"
        elif col in INFRA_FEATURES:
            role = "feature"
            source = "infraestructura"
            description = (
                f"Indicador urbano agregado por alcaldia desde infraestructura snapshot "
                f"{INFRA_SNAPSHOT_YEAR}."
            )
            leakage = "low"
            recommended = True
            temporal = "static_snapshot_2022"
        elif col in MODEL_CONTROL_COLUMNS:
            role = "control" if col != "infraestructura_es_snapshot" else "metadata"
            source = "etl" if col.startswith("infraestructura_") else "fuente"
            description = "Variable de control, trazabilidad o cobertura del panel."
            leakage = (
                "medium_same_year_control"
                if col == "total_delitos_fgj"
                else "low"
            )
            recommended = col != "total_delitos_fgj"
            temporal = (
                "static_snapshot_2022"
                if col.startswith("infraestructura_")
                else "annual"
            )
        else:
            role = "metadata"
            source = "etl"
            description = "Variable auxiliar generada por el ETL."
            leakage = "review"
            recommended = False
            temporal = "metadata"
        rows.append(
            {
                "feature_name": col,
                "source_dataset": source,
                "feature_role": role,
                "data_type": _data_type(modeling_panel[col]),
                "description": description,
                "leakage_risk": leakage,
                "recommended_for_modeling": recommended,
                "temporal_behavior": temporal,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dirs()
    pobreza = read_output_csv(ANALYTICS_DIR / "pobreza_alcaldia_anio.csv")
    delitos = read_output_csv(ANALYTICS_DIR / "delitos_alcaldia_anio.csv")
    infraestructura = read_output_csv(ANALYTICS_DIR / "infraestructura_alcaldia.csv")
    pobreza = clean_string_columns(pobreza)
    delitos = clean_string_columns(delitos)
    infraestructura = clean_string_columns(infraestructura)

    pobreza_years = set(pd.to_numeric(pobreza["anio"], errors="coerce").dropna().astype(int))
    delitos_years = set(pd.to_numeric(delitos["anio"], errors="coerce").dropna().astype(int))
    common_years = sorted(pobreza_years & delitos_years)
    preferred_years = [2016, 2018, 2020]
    panel_years = preferred_years if set(preferred_years).issubset(common_years) else common_years
    if not panel_years:
        raise RuntimeError("No hay años comunes entre pobreza y FGJ para construir el panel.")

    base = pobreza[pobreza["anio"].astype(int).isin(panel_years)].copy()
    delito_cols = [
        "alcaldia_key",
        "anio",
        "total_delitos_fgj",
        "total_robos_patrimoniales",
        "target_robos_patrimoniales_total",
        "robo_a_transeunte",
        "robo_a_negocio",
        "robo_a_casa_habitacion",
        "robo_de_vehiculo",
        "robo_de_accesorios_auto",
        "robo_del_interior_de_vehiculo",
    ]
    delitos = delitos[[c for c in delito_cols if c in delitos.columns]].copy()

    panel = base.merge(delitos, on=["alcaldia_key", "anio"], how="left")
    for col in [TARGET, *FGJ_CONTROL_COLUMNS]:
        if col in panel.columns:
            panel[col] = pd.to_numeric(panel[col], errors="coerce").fillna(0)
        else:
            panel[col] = 0

    infra_cols = [
        "alcaldia_key",
        "colonias_count",
        *INFRA_FEATURES,
        "infraestructura_actualizacion_anio",
        "infraestructura_es_snapshot",
        "infraestructura_uso_recomendado",
    ]
    panel = panel.merge(
        infraestructura[[c for c in infra_cols if c in infraestructura.columns]],
        on="alcaldia_key",
        how="left",
    )
    panel["infraestructura_actualizacion_anio"] = panel[
        "infraestructura_actualizacion_anio"
    ].fillna(INFRA_SNAPSHOT_YEAR)
    panel["infraestructura_es_snapshot"] = panel["infraestructura_es_snapshot"].fillna(True)
    panel["infraestructura_uso_recomendado"] = panel[
        "infraestructura_uso_recomendado"
    ].fillna(INFRA_USE_RECOMMENDED)

    panel = panel.sort_values(["anio", "alcaldia_key"])
    panel_path = ANALYTICS_DIR / "panel_alcaldia_anio.csv"
    write_csv(panel, panel_path)

    modeling_columns = [
        "alcaldia_id",
        "tiempo_id",
        "alcaldia_key",
        "alcaldia_nombre",
        "anio",
        TARGET,
        *SOCIAL_FEATURES,
        *INFRA_FEATURES,
        *MODEL_CONTROL_COLUMNS,
    ]
    for col in modeling_columns:
        if col not in panel.columns:
            panel[col] = np.nan
    modeling_panel = panel[modeling_columns].copy()
    modeling_path = ANALYTICS_DIR / "modeling_panel.csv"
    write_csv(modeling_panel, modeling_path)

    null_report = (
        modeling_panel.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "column_name", 0: "null_count"})
    )
    null_report["row_count"] = len(modeling_panel)
    null_report["null_pct"] = null_report["null_count"] / max(len(modeling_panel), 1)
    write_csv(null_report, REPORTS_DIR / "modeling_panel_nulls.csv")

    feature_catalog = build_feature_catalog(modeling_panel)
    feature_catalog_path = ANALYTICS_DIR / "feature_catalog.csv"
    write_csv(feature_catalog, feature_catalog_path)

    metadata = load_metadata()
    update_metadata(
        analytics_panel={
            "panel_years": panel_years,
            "common_years_pobreza_fgj": common_years,
            "panel_rows": int(len(panel)),
            "modeling_rows": int(len(modeling_panel)),
            "panel_columns": panel.columns.tolist(),
            "modeling_columns": modeling_panel.columns.tolist(),
            "feature_catalog_rows": int(len(feature_catalog)),
            "nulls": {
                row["column_name"]: int(row["null_count"])
                for _, row in null_report.iterrows()
                if int(row["null_count"]) > 0
            },
        },
        source_results=metadata.get("source_results", {}),
    )
    print("Panel analítico y catálogo de features completados.")


if __name__ == "__main__":
    main()
