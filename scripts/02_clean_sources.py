from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from etl_common import (
    ALCALDIA_ID,
    ANALYTICS_DIR,
    CANONICAL_ALCALDIAS,
    CLEAN_DIR,
    CSV_NULL,
    FGJ_YEAR_MAX,
    FGJ_YEAR_MIN,
    INFRA_AVG_VARIABLES,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_YEAR,
    INFRA_TEMPORALITY,
    INFRA_USE_RECOMMENDED,
    INFRA_SUM_VARIABLES,
    ROBBERY_ONLY_DIR,
    ROBO_PATRIMONIAL_SUBTIPOS,
    ROBO_SUBTIPO_COLUMNS,
    ROOT,
    SOCIAL_VARIABLES,
    alcaldia_nombre,
    canonicalize_alcaldia,
    classify_robo_subtipo,
    clean_string_columns,
    colonia_key,
    coerce_numeric,
    detect_encoding,
    detect_input_files,
    ensure_dirs,
    load_metadata,
    normalize_columns,
    normalize_text_key,
    parse_month,
    project_path,
    read_csv_robust,
    update_metadata,
    write_csv,
)


FGJ_CLEAN_COLUMNS = [
    "fecha_hecho",
    "fecha_inicio",
    "anio_hecho_clean",
    "mes_hecho_clean",
    "delito",
    "delito_key",
    "categoria_delito",
    "alcaldia_key",
    "alcaldia_nombre",
    "colonia_key",
    "colonia_hecho",
    "latitud",
    "longitud",
    "subtipo_robo_patrimonial",
    "is_robo_patrimonial",
]


def _path_for(dataset: str) -> Path:
    metadata = load_metadata()
    detected = metadata.get("detected_files") or detect_input_files()
    return project_path(detected[dataset])


def _weighted_mean(group: pd.DataFrame, variable: str, weight_col: str = "factor") -> float:
    valid = group[variable].notna() & group[weight_col].notna()
    if not valid.any():
        return np.nan
    weights = group.loc[valid, weight_col]
    denominator = weights.sum()
    if denominator == 0 or pd.isna(denominator):
        return np.nan
    return float((group.loc[valid, variable] * weights).sum() / denominator)


def clean_pobreza() -> dict:
    path = _path_for("pobreza")
    df = read_csv_robust(path, low_memory=False)
    original_rows = len(df)
    df = normalize_columns(df)
    if "ano" in df.columns and "anio" not in df.columns:
        df = df.rename(columns={"ano": "anio"})
    df = clean_string_columns(df)

    for col in ["entidad", "municipio", "anio", "factor", *SOCIAL_VARIABLES]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["entidad"].eq(9)].copy()
    rows_cdmx = len(df)
    df["alcaldia_key"] = df["municipio"].map(canonicalize_alcaldia)
    df["alcaldia_nombre"] = df["alcaldia_key"].map(alcaldia_nombre)
    df["alcaldia_id"] = df["alcaldia_key"].map(ALCALDIA_ID)
    df = df[df["alcaldia_key"].isin(CANONICAL_ALCALDIAS)].copy()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df = df[df["anio"].notna()].copy()
    df["tiempo_id"] = df["anio"].astype(int) * 100

    write_csv(df, CLEAN_DIR / "pobreza_clean.csv")

    rows = []
    for (alcaldia_key, alcaldia_name, anio), group in df.groupby(
        ["alcaldia_key", "alcaldia_nombre", "anio"], dropna=False
    ):
        row = {
            "alcaldia_key": alcaldia_key,
            "alcaldia_nombre": alcaldia_name,
            "alcaldia_id": ALCALDIA_ID.get(alcaldia_key),
            "anio": int(anio),
            "tiempo_id": int(anio) * 100,
            "n_registros_sociales": int(len(group)),
            "factor_sum": float(group["factor"].sum(skipna=True)),
        }
        for variable in SOCIAL_VARIABLES:
            row[f"{variable}_wmean"] = (
                _weighted_mean(group, variable) if variable in group.columns else np.nan
            )
        rows.append(row)

    pobreza_analytics = pd.DataFrame(rows).sort_values(["anio", "alcaldia_key"])
    write_csv(pobreza_analytics, ANALYTICS_DIR / "pobreza_alcaldia_anio.csv")

    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "cdmx_rows": int(rows_cdmx),
        "clean_rows": int(len(df)),
        "analytics_rows": int(len(pobreza_analytics)),
        "years": sorted([int(x) for x in pobreza_analytics["anio"].dropna().unique()]),
        "alcaldias": sorted(pobreza_analytics["alcaldia_key"].dropna().unique().tolist()),
        "dropped_rows": {
            "fuera_de_cdmx": int(original_rows - rows_cdmx),
            "alcaldia_o_anio_no_validos": int(rows_cdmx - len(df)),
        },
        "columns_clean": df.columns.tolist(),
        "columns_analytics": pobreza_analytics.columns.tolist(),
    }


def clean_infraestructura() -> dict:
    path = _path_for("infraestructura")
    df = read_csv_robust(path, low_memory=False)
    original_rows = len(df)
    df = normalize_columns(df)
    df = clean_string_columns(df)
    df["alcaldia_key"] = df["alcaldia"].map(canonicalize_alcaldia)
    df["alcaldia_nombre"] = df["alcaldia_key"].map(alcaldia_nombre)
    df["alcaldia_id"] = df["alcaldia_key"].map(ALCALDIA_ID)
    df["colonia_key"] = df["colonia"].map(colonia_key)
    df["colonia_nombre"] = df["colonia"].map(
        lambda x: normalize_text_key(x).title() if normalize_text_key(x) else None
    )
    df["infraestructura_actualizacion_anio"] = INFRA_SNAPSHOT_YEAR
    df["infraestructura_es_snapshot"] = True
    df["infraestructura_temporalidad"] = INFRA_TEMPORALITY
    df["infraestructura_uso_recomendado"] = INFRA_USE_RECOMMENDED

    numeric_cols = [c for c in [*INFRA_SUM_VARIABLES, *INFRA_AVG_VARIABLES] if c in df.columns]
    df = coerce_numeric(df, numeric_cols)
    df = df[df["alcaldia_key"].isin(CANONICAL_ALCALDIAS)].copy()
    write_csv(df, CLEAN_DIR / "infraestructura_clean.csv")

    rows = []
    for alcaldia_key, group in df.groupby("alcaldia_key", dropna=False):
        row = {
            "alcaldia_key": alcaldia_key,
            "alcaldia_nombre": alcaldia_nombre(alcaldia_key),
            "alcaldia_id": ALCALDIA_ID.get(alcaldia_key),
            "colonias_count": int(group["colonia_key"].nunique(dropna=True)),
            "infraestructura_actualizacion_anio": INFRA_SNAPSHOT_YEAR,
            "infraestructura_es_snapshot": True,
            "infraestructura_temporalidad": INFRA_TEMPORALITY,
            "infraestructura_uso_recomendado": INFRA_USE_RECOMMENDED,
        }
        for col in INFRA_SUM_VARIABLES:
            if col in group.columns:
                suffix = "total" if col == "alump_sum" else "sum"
                row[f"{col}_{suffix}"] = float(group[col].sum(skipna=True))
        for col in INFRA_AVG_VARIABLES:
            if col in group.columns:
                row[f"{col}_avg"] = float(group[col].mean(skipna=True))

        row["mercados_total"] = row.get("ba8_nomerc_sum", np.nan)
        row["locales_total"] = row.get("ba8_noloca_sum", np.nan)
        row["iluminacion_total"] = row.get("alump_sum_total", np.nan)
        row["iluminacion_promedio"] = row.get("alump_mean_avg", np.nan)
        row["residuos_ton_total"] = row.get("resid_ton_sum", np.nan)
        row["equipamiento_salud_total"] = row.get("ba1_noeqsa_sum", np.nan)
        row["equipamiento_educativo_total"] = row.get("ba3_noeqed_sum", np.nan)
        row["agua_potable_promedio"] = row.get("p_aguapot_avg", np.nan)
        row["electricidad_promedio"] = row.get("p_porcelec_avg", np.nan)
        row["drenaje_promedio"] = row.get("r_val_dren_avg", np.nan)
        rows.append(row)

    infraestructura_analytics = pd.DataFrame(rows).sort_values("alcaldia_key")
    for feature in INFRA_FEATURES:
        if feature not in infraestructura_analytics.columns:
            infraestructura_analytics[feature] = np.nan
    write_csv(infraestructura_analytics, ANALYTICS_DIR / "infraestructura_alcaldia.csv")

    missing = sorted(set(CANONICAL_ALCALDIAS) - set(infraestructura_analytics["alcaldia_key"]))
    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "clean_rows": int(len(df)),
        "analytics_rows": int(len(infraestructura_analytics)),
        "alcaldias": sorted(infraestructura_analytics["alcaldia_key"].dropna().unique().tolist()),
        "missing_alcaldias": missing,
        "columns_clean": df.columns.tolist(),
        "columns_analytics": infraestructura_analytics.columns.tolist(),
        "aggregation_notes": {
            "sumadas": INFRA_SUM_VARIABLES,
            "promediadas": INFRA_AVG_VARIABLES,
            "ambiguas": (
                "Variables con prefijos p_, r_, s_ y c_ se trataron como porcentajes, "
                "ranking, valor relativo o promedio y se agregaron por media."
            ),
        },
    }


def _best_alcaldia(chunk: pd.DataFrame) -> pd.Series:
    hecho = chunk.get("alcaldia_hecho", pd.Series([np.nan] * len(chunk), index=chunk.index))
    catalogo = chunk.get("alcaldia_catalogo", pd.Series([np.nan] * len(chunk), index=chunk.index))
    alcaldia_from_hecho = hecho.map(canonicalize_alcaldia)
    alcaldia_from_catalogo = catalogo.map(canonicalize_alcaldia)
    return alcaldia_from_hecho.fillna(alcaldia_from_catalogo)


def _append_csv(df: pd.DataFrame, path: Path, header_written: bool) -> bool:
    df.to_csv(
        path,
        mode="a",
        header=not header_written,
        index=False,
        encoding="utf-8",
        na_rep=CSV_NULL,
    )
    return True


def clean_fgj(chunksize: int = 250_000) -> dict:
    path = _path_for("fgj")
    output_clean = CLEAN_DIR / "fgj_clean.csv"
    output_robbery = ROBBERY_ONLY_DIR / "fgj_robos_patrimoniales_clean.csv"
    for output in [output_clean, output_robbery, ANALYTICS_DIR / "delitos_alcaldia_mes_subtipo.csv"]:
        if output.exists():
            output.unlink()

    general_annual_parts = []
    robbery_monthly_parts = []
    robbery_annual_parts = []
    original_rows = 0
    final_rows = 0
    robbery_rows = 0
    invalid_alcaldia_rows = 0
    invalid_year_month_rows = 0
    out_of_project_year_rows = 0
    coord_out_of_range = 0
    coord_valid_total = 0
    coord_missing_total = 0
    header_general_written = False
    header_robbery_written = False
    raw_years_seen: set[int] = set()
    cleaned_years_seen: set[int] = set()
    alcaldias_seen: set[str] = set()

    encoding = detect_encoding(path)
    for chunk in pd.read_csv(path, encoding=encoding, chunksize=chunksize, low_memory=False):
        original_rows += len(chunk)
        chunk = normalize_columns(chunk)
        chunk = clean_string_columns(chunk)

        fecha_hecho = pd.to_datetime(chunk.get("fecha_hecho"), errors="coerce")
        fecha_inicio = pd.to_datetime(chunk.get("fecha_inicio"), errors="coerce")
        anio_numeric = pd.to_numeric(chunk.get("anio_hecho"), errors="coerce")
        chunk["anio_hecho_clean"] = anio_numeric.fillna(fecha_hecho.dt.year)
        raw_years_seen.update(
            int(x)
            for x in pd.to_numeric(chunk["anio_hecho_clean"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )

        mes_from_fecha = fecha_hecho.dt.month
        mes_from_text = chunk.get("mes_hecho", pd.Series([np.nan] * len(chunk))).map(parse_month)
        chunk["mes_hecho_clean"] = pd.to_numeric(mes_from_fecha.fillna(mes_from_text), errors="coerce")
        chunk["alcaldia_key"] = _best_alcaldia(chunk)
        chunk["alcaldia_nombre"] = chunk["alcaldia_key"].map(alcaldia_nombre)
        chunk["latitud"] = pd.to_numeric(chunk.get("latitud"), errors="coerce")
        chunk["longitud"] = pd.to_numeric(chunk.get("longitud"), errors="coerce")
        chunk["delito"] = chunk.get("delito", pd.Series([np.nan] * len(chunk))).astype("string").str.strip()
        chunk["categoria_delito"] = (
            chunk.get("categoria_delito", pd.Series([np.nan] * len(chunk))).astype("string").str.strip()
        )
        chunk["delito_key"] = chunk["delito"].map(normalize_text_key)
        chunk["subtipo_robo_patrimonial"] = chunk["delito_key"].map(classify_robo_subtipo)
        chunk["is_robo_patrimonial"] = (
            chunk["subtipo_robo_patrimonial"].isin(ROBO_PATRIMONIAL_SUBTIPOS).astype(int)
        )
        chunk["fecha_hecho"] = fecha_hecho.dt.strftime("%Y-%m-%d")
        chunk["fecha_inicio"] = fecha_inicio.dt.strftime("%Y-%m-%d")

        invalid_alcaldia_rows += int(chunk["alcaldia_key"].isna().sum())
        valid_year_month = (
            chunk["anio_hecho_clean"].between(FGJ_YEAR_MIN, FGJ_YEAR_MAX)
            & chunk["mes_hecho_clean"].between(1, 12)
        )
        parseable_year_month = (
            chunk["anio_hecho_clean"].notna() & chunk["mes_hecho_clean"].between(1, 12)
        )
        invalid_year_month_rows += int((~parseable_year_month).sum())
        out_of_project_year_rows += int((parseable_year_month & ~valid_year_month).sum())

        valid = chunk[chunk["alcaldia_key"].isin(CANONICAL_ALCALDIAS) & valid_year_month].copy()
        if valid.empty:
            continue

        valid["anio_hecho_clean"] = valid["anio_hecho_clean"].astype(int)
        valid["mes_hecho_clean"] = valid["mes_hecho_clean"].astype(int)
        valid["tiempo_id"] = valid["anio_hecho_clean"] * 100 + valid["mes_hecho_clean"]
        valid["colonia_hecho"] = valid.get("colonia_hecho", pd.Series([np.nan] * len(valid))).fillna(
            valid.get("colonia_catalogo", pd.Series([np.nan] * len(valid)))
        )
        valid["colonia_key"] = valid["colonia_hecho"].map(colonia_key)
        valid["coord_valid"] = valid["latitud"].notna() & valid["longitud"].notna()
        valid["latitud_para_promedio"] = valid["latitud"].where(valid["coord_valid"])
        valid["longitud_para_promedio"] = valid["longitud"].where(valid["coord_valid"])

        coord_valid_total += int(valid["coord_valid"].sum())
        coord_missing_total += int((~valid["coord_valid"]).sum())
        coord_in_range = valid["latitud"].between(19.0, 19.7) & valid["longitud"].between(-99.4, -98.8)
        coord_out_of_range += int((valid["coord_valid"] & ~coord_in_range).sum())

        cleaned_years_seen.update(valid["anio_hecho_clean"].dropna().astype(int).unique().tolist())
        alcaldias_seen.update(valid["alcaldia_key"].dropna().unique().tolist())
        final_rows += len(valid)

        general_annual = (
            valid.groupby(["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"], dropna=False)
            .agg(total_delitos_fgj=("delito", "size"), total_robos_patrimoniales=("is_robo_patrimonial", "sum"))
            .reset_index()
        )
        general_annual_parts.append(general_annual)

        clean_ready = valid[FGJ_CLEAN_COLUMNS].copy()
        header_general_written = _append_csv(clean_ready, output_clean, header_general_written)

        robbery = valid[valid["is_robo_patrimonial"].eq(1)].copy()
        if robbery.empty:
            continue
        robbery_rows += len(robbery)
        header_robbery_written = _append_csv(robbery[FGJ_CLEAN_COLUMNS], output_robbery, header_robbery_written)

        robbery_monthly = (
            robbery.groupby(
                [
                    "alcaldia_key",
                    "alcaldia_nombre",
                    "anio_hecho_clean",
                    "mes_hecho_clean",
                    "subtipo_robo_patrimonial",
                ],
                dropna=False,
            )
            .agg(
                total_robos_patrimoniales=("delito", "size"),
                registros_con_coordenadas=("coord_valid", "sum"),
                latitud_sum=("latitud_para_promedio", "sum"),
                longitud_sum=("longitud_para_promedio", "sum"),
            )
            .reset_index()
        )
        robbery_monthly_parts.append(robbery_monthly)

        robbery_annual = (
            robbery.groupby(
                ["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean", "subtipo_robo_patrimonial"],
                dropna=False,
            )
            .agg(total_robos_patrimoniales=("delito", "size"))
            .reset_index()
        )
        robbery_annual_parts.append(robbery_annual)

    general_annual_final = _build_general_annual(general_annual_parts)
    robbery_monthly_final = _build_robbery_monthly(robbery_monthly_parts)
    robbery_annual_final = _build_robbery_annual(robbery_annual_parts)

    write_csv(general_annual_final, ANALYTICS_DIR / "delitos_alcaldia_anio.csv")
    write_csv(robbery_monthly_final, ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_mes_subtipo.csv")
    write_csv(robbery_annual_final, ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_anio.csv")

    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "clean_rows": int(final_rows),
        "robbery_rows": int(robbery_rows),
        "analytics_general_annual_rows": int(len(general_annual_final)),
        "robbery_month_rows": int(len(robbery_monthly_final)),
        "robbery_annual_rows": int(len(robbery_annual_final)),
        "raw_years": sorted(raw_years_seen),
        "raw_year_range": [min(raw_years_seen), max(raw_years_seen)] if raw_years_seen else [],
        "years": sorted(cleaned_years_seen),
        "clean_year_range": [min(cleaned_years_seen), max(cleaned_years_seen)] if cleaned_years_seen else [],
        "alcaldias": sorted(alcaldias_seen),
        "dropped_rows": {
            "alcaldia_no_valida": int(invalid_alcaldia_rows),
            "anio_o_mes_no_parseable": int(invalid_year_month_rows),
            "fuera_rango_proyecto_2016_2025": int(out_of_project_year_rows),
        },
        "coordinates": {
            "validas": int(coord_valid_total),
            "faltantes": int(coord_missing_total),
            "fuera_rango_aproximado_cdmx": int(coord_out_of_range),
        },
        "columns_clean": FGJ_CLEAN_COLUMNS,
        "columns_analytics_general_annual": general_annual_final.columns.tolist(),
        "columns_robbery_month": robbery_monthly_final.columns.tolist(),
        "columns_robbery_annual": robbery_annual_final.columns.tolist(),
    }


def _build_general_annual(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    grouped = (
        pd.concat(parts, ignore_index=True)
        .groupby(["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"], dropna=False)
        .agg(total_delitos_fgj=("total_delitos_fgj", "sum"), total_robos_patrimoniales=("total_robos_patrimoniales", "sum"))
        .reset_index()
        .rename(columns={"anio_hecho_clean": "anio"})
    )
    grouped["total_no_robos_patrimoniales"] = grouped["total_delitos_fgj"] - grouped["total_robos_patrimoniales"]
    grouped["share_robos_patrimoniales_sobre_total_delitos"] = grouped["total_robos_patrimoniales"] / grouped[
        "total_delitos_fgj"
    ].replace({0: np.nan})
    grouped["tiempo_id"] = grouped["anio"].astype(int) * 100
    grouped["alcaldia_id"] = grouped["alcaldia_key"].map(ALCALDIA_ID)
    return grouped[
        [
            "alcaldia_key",
            "alcaldia_nombre",
            "alcaldia_id",
            "anio",
            "tiempo_id",
            "total_delitos_fgj",
            "total_robos_patrimoniales",
            "total_no_robos_patrimoniales",
            "share_robos_patrimoniales_sobre_total_delitos",
        ]
    ].sort_values(["anio", "alcaldia_key"])


def _build_robbery_monthly(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    monthly = (
        pd.concat(parts, ignore_index=True)
        .groupby(
            [
                "alcaldia_key",
                "alcaldia_nombre",
                "anio_hecho_clean",
                "mes_hecho_clean",
                "subtipo_robo_patrimonial",
            ],
            dropna=False,
        )
        .agg(
            total_robos_patrimoniales=("total_robos_patrimoniales", "sum"),
            registros_con_coordenadas=("registros_con_coordenadas", "sum"),
            latitud_sum=("latitud_sum", "sum"),
            longitud_sum=("longitud_sum", "sum"),
        )
        .reset_index()
        .rename(columns={"anio_hecho_clean": "anio", "mes_hecho_clean": "mes"})
    )
    monthly["latitud_promedio"] = monthly["latitud_sum"] / monthly["registros_con_coordenadas"].replace({0: np.nan})
    monthly["longitud_promedio"] = monthly["longitud_sum"] / monthly["registros_con_coordenadas"].replace({0: np.nan})
    monthly["tiempo_id"] = monthly["anio"].astype(int) * 100 + monthly["mes"].astype(int)
    monthly["alcaldia_id"] = monthly["alcaldia_key"].map(ALCALDIA_ID)
    return monthly[
        [
            "alcaldia_key",
            "alcaldia_nombre",
            "alcaldia_id",
            "anio",
            "mes",
            "tiempo_id",
            "subtipo_robo_patrimonial",
            "total_robos_patrimoniales",
            "registros_con_coordenadas",
            "latitud_promedio",
            "longitud_promedio",
        ]
    ].sort_values(["anio", "mes", "alcaldia_key", "subtipo_robo_patrimonial"])


def _build_robbery_annual(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    grouped = (
        pd.concat(parts, ignore_index=True)
        .groupby(["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean", "subtipo_robo_patrimonial"], dropna=False)
        .agg(total_robos_patrimoniales=("total_robos_patrimoniales", "sum"))
        .reset_index()
    )
    base = (
        grouped.groupby(["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"], dropna=False)
        .agg(target_robos_patrimoniales_total=("total_robos_patrimoniales", "sum"))
        .reset_index()
    )
    pivot = (
        grouped.pivot_table(
            index=["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"],
            columns="subtipo_robo_patrimonial",
            values="total_robos_patrimoniales",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    annual = base.merge(pivot, on=["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"], how="left")
    for subtype, col in ROBO_SUBTIPO_COLUMNS.items():
        annual[col] = annual.get(subtype, 0)
    annual = annual.drop(columns=[c for c in annual.columns if c in ROBO_PATRIMONIAL_SUBTIPOS], errors="ignore")
    annual = annual.rename(columns={"anio_hecho_clean": "anio"})
    annual["target_robos_log1p"] = np.log1p(annual["target_robos_patrimoniales_total"])
    annual["tiempo_id"] = annual["anio"].astype(int) * 100
    annual["alcaldia_id"] = annual["alcaldia_key"].map(ALCALDIA_ID)
    return annual[
        [
            "alcaldia_key",
            "alcaldia_nombre",
            "alcaldia_id",
            "anio",
            "tiempo_id",
            "target_robos_patrimoniales_total",
            *ROBO_SUBTIPO_COLUMNS.values(),
            "target_robos_log1p",
        ]
    ].sort_values(["anio", "alcaldia_key"])


def main() -> None:
    ensure_dirs()
    source_results = {
        "pobreza": clean_pobreza(),
        "infraestructura": clean_infraestructura(),
        "fgj": clean_fgj(),
    }
    update_metadata(source_results=source_results)
    print("Limpieza de fuentes completada.")


if __name__ == "__main__":
    main()
