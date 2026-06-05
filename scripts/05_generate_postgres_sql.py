from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from etl_common import (
    ANALYTICS_DIR,
    CLEAN_DIR,
    DIMENSIONAL_DIR,
    ROBBERY_ONLY_DIR,
    ROOT,
    SQL_DIR,
    ensure_dirs,
    is_snake_case,
)


CLEAN_TABLES = {
    "pobreza_clean": CLEAN_DIR / "pobreza_clean.csv",
    "infraestructura_clean": CLEAN_DIR / "infraestructura_clean.csv",
    "fgj_clean": CLEAN_DIR / "fgj_clean.csv",
}
ANALYTICS_TABLES = {
    "pobreza_alcaldia_anio": ANALYTICS_DIR / "pobreza_alcaldia_anio.csv",
    "infraestructura_alcaldia": ANALYTICS_DIR / "infraestructura_alcaldia.csv",
    "delitos_alcaldia_anio": ANALYTICS_DIR / "delitos_alcaldia_anio.csv",
    "fgj_robos_patrimoniales_clean": ROBBERY_ONLY_DIR / "fgj_robos_patrimoniales_clean.csv",
    "robos_patrimoniales_alcaldia_mes_subtipo": ROBBERY_ONLY_DIR
    / "robos_patrimoniales_alcaldia_mes_subtipo.csv",
    "robos_patrimoniales_alcaldia_anio": ROBBERY_ONLY_DIR
    / "robos_patrimoniales_alcaldia_anio.csv",
    "panel_alcaldia_anio": ANALYTICS_DIR / "panel_alcaldia_anio.csv",
    "modeling_panel": ANALYTICS_DIR / "modeling_panel.csv",
    "feature_catalog": ANALYTICS_DIR / "feature_catalog.csv",
}
DIMENSIONAL_TABLES = {
    "dim_alcaldia": DIMENSIONAL_DIR / "dim_alcaldia.csv",
    "dim_tiempo": DIMENSIONAL_DIR / "dim_tiempo.csv",
    "dim_colonia": DIMENSIONAL_DIR / "dim_colonia.csv",
    "dim_delito_subtipo": DIMENSIONAL_DIR / "dim_delito_subtipo.csv",
    "dim_variable_social": DIMENSIONAL_DIR / "dim_variable_social.csv",
    "dim_variable_infraestructura": DIMENSIONAL_DIR / "dim_variable_infraestructura.csv",
    "dim_fuente_datos": DIMENSIONAL_DIR / "dim_fuente_datos.csv",
    "fact_delitos_generales_alcaldia_anio": DIMENSIONAL_DIR
    / "fact_delitos_generales_alcaldia_anio.csv",
    "fact_robos_patrimoniales_alcaldia_mes_subtipo": DIMENSIONAL_DIR
    / "fact_robos_patrimoniales_alcaldia_mes_subtipo.csv",
    "fact_robos_patrimoniales_alcaldia_anio": DIMENSIONAL_DIR
    / "fact_robos_patrimoniales_alcaldia_anio.csv",
    "fact_pobreza_alcaldia_anio": DIMENSIONAL_DIR / "fact_pobreza_alcaldia_anio.csv",
    "fact_infraestructura_alcaldia": DIMENSIONAL_DIR / "fact_infraestructura_alcaldia.csv",
    "fact_infraestructura_colonia": DIMENSIONAL_DIR / "fact_infraestructura_colonia.csv",
    "fact_panel_analitico_alcaldia_anio": DIMENSIONAL_DIR
    / "fact_panel_analitico_alcaldia_anio.csv",
}


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def sample_frame(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8", na_values=[r"\N"], nrows=5000)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=read_header(path))


def infer_sql_type(column: str, sample: pd.Series | None) -> str:
    if column.startswith("fecha_"):
        return "date"
    if column.startswith("hora_"):
        return "time"
    if column == "is_robo_patrimonial":
        return "integer"
    if (
        column.startswith("es_")
        or column.endswith("_snapshot")
        or column.startswith("recomendada_")
        or column == "recommended_for_modeling"
    ):
        return "boolean"
    if column.endswith("_id") or column in {
        "anio",
        "mes",
        "trimestre",
        "municipio_enigh",
        "cve_ent",
        "infraestructura_actualizacion_anio",
        "n_registros_sociales",
        "registros_con_coordenadas",
    }:
        return "integer"
    if (
        column.startswith("total_")
        or column.endswith("_total")
        or column.endswith("_sum")
        or column.endswith("_count")
        or column.startswith("robo_")
        or column == "colonias_count"
    ):
        return "bigint"
    if column.startswith("share_") or column.endswith("_log1p"):
        return "double precision"
    if column in {"latitud", "longitud", "latitud_promedio", "longitud_promedio"}:
        return "double precision"
    if re.search(r"(_wmean|_avg|_mean|_promedio|_pct|factor_sum|resid_ton)", column):
        return "double precision"
    if sample is not None:
        numeric = pd.to_numeric(sample.dropna(), errors="coerce")
        if len(numeric) and numeric.notna().all():
            if (numeric % 1 == 0).all():
                return "bigint"
            return "double precision"
    return "text"


def create_table_sql(schema: str, table: str, path: Path) -> str:
    header = read_header(path)
    frame = sample_frame(path)
    column_lines = []
    for col in header:
        if not is_snake_case(col):
            raise ValueError(f"Columna no snake_case en {path}: {col}")
        sample = frame[col] if col in frame.columns else None
        column_lines.append(f"    {col} {infer_sql_type(col, sample)}")
    columns_sql = ",\n".join(column_lines)
    return f"CREATE TABLE IF NOT EXISTS {schema}.{table} (\n{columns_sql}\n);\n"


def copy_sql(schema: str, table: str, path: Path) -> str:
    header = read_header(path)
    rel = path.relative_to(ROOT).as_posix()
    columns = ", ".join(header)
    return (
        f"\\copy {schema}.{table} ({columns}) FROM '{rel}' "
        "WITH (FORMAT csv, HEADER true, NULL '\\N', ENCODING 'UTF8');"
    )


def write_create_file(filename: str, schema: str, tables: dict[str, Path]) -> None:
    parts = [
        "-- Ejecutar desde PostgreSQL despues de crear la base de datos.\n",
        f"-- Tablas en esquema {schema}.\n\n",
    ]
    for table, path in tables.items():
        parts.append(create_table_sql(schema, table, path))
        parts.append("\n")
    (SQL_DIR / filename).write_text("".join(parts), encoding="utf-8")


def write_copy_file(filename: str, schema: str, tables: dict[str, Path]) -> None:
    lines = [
        "-- Ejecutar desde la raiz del proyecto o ajustar rutas relativas.\n",
        "-- Los CSV usan UTF-8 y NULL '\\N'.\n\n",
    ]
    for table, path in tables.items():
        lines.append(copy_sql(schema, table, path))
        lines.append("\n")
    (SQL_DIR / filename).write_text("".join(lines), encoding="utf-8")


def constraint_sql() -> str:
    return """-- Llaves, restricciones e indices principales.

ALTER TABLE analytics.pobreza_alcaldia_anio ADD CONSTRAINT pk_pobreza_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.infraestructura_alcaldia ADD CONSTRAINT pk_infraestructura_alcaldia PRIMARY KEY (alcaldia_key);
ALTER TABLE analytics.delitos_alcaldia_anio ADD CONSTRAINT pk_delitos_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT pk_robos_mes_subtipo PRIMARY KEY (alcaldia_key, anio, mes, subtipo_robo_patrimonial);
ALTER TABLE analytics.robos_patrimoniales_alcaldia_anio ADD CONSTRAINT pk_robos_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.panel_alcaldia_anio ADD CONSTRAINT pk_panel_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.modeling_panel ADD CONSTRAINT pk_modeling_panel PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.feature_catalog ADD CONSTRAINT pk_feature_catalog PRIMARY KEY (feature_name);

ALTER TABLE dw.dim_alcaldia ADD CONSTRAINT pk_dim_alcaldia PRIMARY KEY (alcaldia_id);
ALTER TABLE dw.dim_tiempo ADD CONSTRAINT pk_dim_tiempo PRIMARY KEY (tiempo_id);
ALTER TABLE dw.dim_colonia ADD CONSTRAINT pk_dim_colonia PRIMARY KEY (colonia_id);
ALTER TABLE dw.dim_delito_subtipo ADD CONSTRAINT pk_dim_delito_subtipo PRIMARY KEY (delito_subtipo_id);
ALTER TABLE dw.dim_variable_social ADD CONSTRAINT pk_dim_variable_social PRIMARY KEY (variable_social_id);
ALTER TABLE dw.dim_variable_infraestructura ADD CONSTRAINT pk_dim_variable_infraestructura PRIMARY KEY (variable_infraestructura_id);
ALTER TABLE dw.dim_fuente_datos ADD CONSTRAINT pk_dim_fuente_datos PRIMARY KEY (fuente_datos_id);

ALTER TABLE dw.dim_alcaldia ADD CONSTRAINT uq_dim_alcaldia_key UNIQUE (alcaldia_key);
ALTER TABLE dw.dim_tiempo ADD CONSTRAINT uq_dim_tiempo_anio_mes UNIQUE (anio, mes);
ALTER TABLE dw.dim_colonia ADD CONSTRAINT uq_dim_colonia_natural UNIQUE (alcaldia_id, colonia_key, cve_col);
ALTER TABLE dw.dim_delito_subtipo ADD CONSTRAINT uq_dim_delito_subtipo UNIQUE (subtipo_robo_patrimonial);
ALTER TABLE dw.dim_variable_social ADD CONSTRAINT uq_dim_variable_social UNIQUE (variable_nombre);
ALTER TABLE dw.dim_variable_infraestructura ADD CONSTRAINT uq_dim_variable_infraestructura UNIQUE (variable_nombre);
ALTER TABLE dw.dim_fuente_datos ADD CONSTRAINT uq_dim_fuente_datos UNIQUE (fuente_nombre);

ALTER TABLE dw.fact_delitos_generales_alcaldia_anio ADD CONSTRAINT pk_fact_delitos_generales PRIMARY KEY (alcaldia_id, tiempo_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT pk_fact_robos_mes_subtipo PRIMARY KEY (alcaldia_id, tiempo_id, delito_subtipo_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_anio ADD CONSTRAINT pk_fact_robos_anio PRIMARY KEY (alcaldia_id, tiempo_id);
ALTER TABLE dw.fact_pobreza_alcaldia_anio ADD CONSTRAINT pk_fact_pobreza_anio PRIMARY KEY (alcaldia_id, tiempo_id);
ALTER TABLE dw.fact_infraestructura_alcaldia ADD CONSTRAINT pk_fact_infra_alcaldia PRIMARY KEY (alcaldia_id, snapshot_tiempo_id);
ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT pk_fact_infra_colonia PRIMARY KEY (colonia_id, snapshot_tiempo_id);
ALTER TABLE dw.fact_panel_analitico_alcaldia_anio ADD CONSTRAINT pk_fact_panel PRIMARY KEY (alcaldia_id, tiempo_id);

ALTER TABLE dw.dim_colonia ADD CONSTRAINT fk_dim_colonia_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);

ALTER TABLE dw.fact_delitos_generales_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_generales_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_delitos_generales_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_generales_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_delitos_generales_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_generales_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_robos_mes_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_robos_mes_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_robos_mes_subtipo FOREIGN KEY (delito_subtipo_id) REFERENCES dw.dim_delito_subtipo(delito_subtipo_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_robos_mes_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_anio ADD CONSTRAINT fk_fact_robos_anio_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_anio ADD CONSTRAINT fk_fact_robos_anio_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_robos_patrimoniales_alcaldia_anio ADD CONSTRAINT fk_fact_robos_anio_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_pobreza_alcaldia_anio ADD CONSTRAINT fk_fact_pobreza_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_pobreza_alcaldia_anio ADD CONSTRAINT fk_fact_pobreza_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_pobreza_alcaldia_anio ADD CONSTRAINT fk_fact_pobreza_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_infraestructura_alcaldia ADD CONSTRAINT fk_fact_infra_alcaldia_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_infraestructura_alcaldia ADD CONSTRAINT fk_fact_infra_alcaldia_tiempo FOREIGN KEY (snapshot_tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_infraestructura_alcaldia ADD CONSTRAINT fk_fact_infra_alcaldia_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT fk_fact_infra_colonia_colonia FOREIGN KEY (colonia_id) REFERENCES dw.dim_colonia(colonia_id);
ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT fk_fact_infra_colonia_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT fk_fact_infra_colonia_tiempo FOREIGN KEY (snapshot_tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT fk_fact_infra_colonia_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_panel_analitico_alcaldia_anio ADD CONSTRAINT fk_fact_panel_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_panel_analitico_alcaldia_anio ADD CONSTRAINT fk_fact_panel_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_panel_analitico_alcaldia_anio ADD CONSTRAINT fk_fact_panel_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

CREATE INDEX IF NOT EXISTS idx_dw_dim_colonia_alcaldia_id ON dw.dim_colonia (alcaldia_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_delitos_generales_alcaldia_tiempo ON dw.fact_delitos_generales_alcaldia_anio (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_robos_mes_alcaldia_tiempo ON dw.fact_robos_patrimoniales_alcaldia_mes_subtipo (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_robos_mes_subtipo ON dw.fact_robos_patrimoniales_alcaldia_mes_subtipo (delito_subtipo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_robos_anio_alcaldia_tiempo ON dw.fact_robos_patrimoniales_alcaldia_anio (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_pobreza_alcaldia_tiempo ON dw.fact_pobreza_alcaldia_anio (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_infra_alcaldia_snapshot ON dw.fact_infraestructura_alcaldia (alcaldia_id, snapshot_tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_infra_colonia_snapshot ON dw.fact_infraestructura_colonia (alcaldia_id, snapshot_tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_panel_alcaldia_tiempo ON dw.fact_panel_analitico_alcaldia_anio (alcaldia_id, tiempo_id);
"""


def validation_sql() -> str:
    return """-- Consultas de validacion posteriores a la carga.

SELECT 'dw.dim_alcaldia_count' AS check_name, COUNT(*) AS value FROM dw.dim_alcaldia;
SELECT 'dw.dim_delito_subtipo_count' AS check_name, COUNT(*) AS value FROM dw.dim_delito_subtipo;
SELECT 'panel_rows' AS check_name, COUNT(*) AS value FROM analytics.panel_alcaldia_anio;
SELECT anio, COUNT(DISTINCT alcaldia_key) AS alcaldias FROM analytics.panel_alcaldia_anio GROUP BY anio ORDER BY anio;
SELECT COUNT(*) AS fgj_years_outside FROM clean.fgj_clean WHERE anio_hecho_clean NOT BETWEEN 2016 AND 2025;
SELECT COUNT(*) AS robbery_otro_rows FROM analytics.fgj_robos_patrimoniales_clean WHERE subtipo_robo_patrimonial = 'OTRO';
SELECT COUNT(*) AS infra_snapshot_rows FROM dw.fact_infraestructura_alcaldia WHERE snapshot_tiempo_id = 202200 AND infraestructura_actualizacion_anio = 2022 AND infraestructura_es_snapshot IS TRUE;
SELECT COUNT(*) AS facts_without_alcaldia
FROM dw.fact_panel_analitico_alcaldia_anio f
LEFT JOIN dw.dim_alcaldia d ON d.alcaldia_id = f.alcaldia_id
WHERE d.alcaldia_id IS NULL;
SELECT feature_role, COUNT(*) FROM analytics.feature_catalog GROUP BY feature_role ORDER BY feature_role;
"""


def drop_sql() -> str:
    return """-- Borra todos los esquemas generados por este proyecto. Usar con cuidado.
DROP SCHEMA IF EXISTS dw CASCADE;
DROP SCHEMA IF EXISTS analytics CASCADE;
DROP SCHEMA IF EXISTS clean CASCADE;
"""


def write_readme() -> None:
    text = """# Mineria de datos CDMX

ETL reproducible para explorar asociaciones entre pobreza multidimensional, infraestructura urbana y robos patrimoniales por alcaldia de la Ciudad de Mexico. El proyecto no afirma causalidad; deja datos listos para EDA, BI, ML exploratorio e implementacion posterior en PostgreSQL.

## Fuentes

- `datasets/`: CSV originales, sin modificarlos.
- `Documentacion/`: diccionario MMIP y material complementario si esta disponible.

## Estructura

- `data/processed/clean/`: fuentes limpias.
- `data/processed/analytics/`: panel, agregados y catalogo de features.
- `data/processed/robbery_only/`: FGJ y agregados solo de robos patrimoniales.
- `dimensional_schema/`: dimensiones y hechos para BI/PostgreSQL.
- `sql/`: scripts de creacion, carga y validacion.
- `reports/etl_report.md`: informe breve del ETL.

## Ejecucion

```bash
python scripts/run_etl.py
```

## FGJ general vs robos patrimoniales

`data/processed/clean/fgj_clean.csv` conserva delitos validos de FGJ entre 2016 y 2025. Puede contener `OTRO` para trazabilidad.

`data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv` contiene exclusivamente registros con `is_robo_patrimonial = 1`. `OTRO` no aparece en esta capa ni en hechos de robos patrimoniales.

Los seis subtipos patrimoniales son: `ROBO_A_TRANSEUNTE`, `ROBO_A_NEGOCIO`, `ROBO_A_CASA_HABITACION`, `ROBO_DE_VEHICULO`, `ROBO_DE_ACCESORIOS_AUTO` y `ROBO_DEL_INTERIOR_DE_VEHICULO`.

## Infraestructura

Infraestructura es snapshot estructural 2022:

- `infraestructura_actualizacion_anio = 2022`
- `infraestructura_es_snapshot = true`
- `infraestructura_temporalidad = static_snapshot_2022`

No debe interpretarse como medicion anual.

## Panel y ML

El panel principal usa los anios comunes entre pobreza y FGJ. Si existen, se usan 2016, 2018 y 2020, con meta de 48 filas: 16 alcaldias por 3 anios.

Para EDA usa `data/processed/analytics/panel_alcaldia_anio.csv`. Para ML exploratorio usa `data/processed/analytics/modeling_panel.csv`. El ETL no escala ni imputa silenciosamente. Las columnas derivadas del target se documentan en `feature_catalog.csv` y no se recomiendan como predictores.

## BI y esquema dimensional

Para BI usa `dimensional_schema/`. Para robos mensuales usa `fact_robos_patrimoniales_alcaldia_mes_subtipo`. Para delitos generales de control usa `fact_delitos_generales_alcaldia_anio`.

```mermaid
erDiagram
dim_alcaldia ||--o{ dim_colonia : alcaldia_id
dim_alcaldia ||--o{ fact_delitos_generales_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_delitos_generales_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_delitos_generales_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : alcaldia_id
dim_tiempo ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : tiempo_id
dim_delito_subtipo ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : delito_subtipo_id
dim_fuente_datos ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : fuente_datos_id
dim_alcaldia ||--o{ fact_robos_patrimoniales_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_robos_patrimoniales_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_robos_patrimoniales_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_pobreza_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_pobreza_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_pobreza_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_infraestructura_alcaldia : alcaldia_id
dim_tiempo ||--o{ fact_infraestructura_alcaldia : snapshot_tiempo_id
dim_fuente_datos ||--o{ fact_infraestructura_alcaldia : fuente_datos_id
dim_colonia ||--o{ fact_infraestructura_colonia : colonia_id
dim_alcaldia ||--o{ fact_infraestructura_colonia : alcaldia_id
dim_tiempo ||--o{ fact_infraestructura_colonia : snapshot_tiempo_id
dim_fuente_datos ||--o{ fact_infraestructura_colonia : fuente_datos_id
dim_alcaldia ||--o{ fact_panel_analitico_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_panel_analitico_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_panel_analitico_alcaldia_anio : fuente_datos_id
```

## Carga futura en PostgreSQL

Los scripts SQL no se ejecutan automaticamente. Crear la base manualmente:

```bash
createdb mineria_cdmx
psql -d mineria_cdmx
```

Dentro de `psql`, desde la raiz del proyecto:

```sql
\\i sql/01_create_schemas.sql
\\i sql/02_create_clean_tables.sql
\\i sql/03_create_analytics_tables.sql
\\i sql/04_create_dimensional_schema.sql
\\i sql/05_create_indexes_and_constraints.sql
\\i sql/06_copy_clean_csv.sql
\\i sql/07_copy_analytics_csv.sql
\\i sql/08_copy_dimensional_csv.sql
\\i sql/09_validation_queries.sql
```

Alternativa desde terminal:

```bash
psql -d mineria_cdmx -f sql/01_create_schemas.sql
psql -d mineria_cdmx -f sql/02_create_clean_tables.sql
psql -d mineria_cdmx -f sql/03_create_analytics_tables.sql
psql -d mineria_cdmx -f sql/04_create_dimensional_schema.sql
psql -d mineria_cdmx -f sql/05_create_indexes_and_constraints.sql
psql -d mineria_cdmx -f sql/06_copy_clean_csv.sql
psql -d mineria_cdmx -f sql/07_copy_analytics_csv.sql
psql -d mineria_cdmx -f sql/08_copy_dimensional_csv.sql
psql -d mineria_cdmx -f sql/09_validation_queries.sql
```

Los `COPY` usan rutas relativas y deben ejecutarse desde la raiz del proyecto o ajustar rutas.
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    (SQL_DIR / "00_create_database_notes.md").write_text(
        "# Base de datos\n\n"
        "Este proyecto no crea ni conecta PostgreSQL automaticamente. Crear `mineria_cdmx` manualmente y ejecutar los scripts desde la raiz del proyecto.\n",
        encoding="utf-8",
    )
    (SQL_DIR / "01_create_schemas.sql").write_text(
        "CREATE SCHEMA IF NOT EXISTS clean;\n"
        "CREATE SCHEMA IF NOT EXISTS analytics;\n"
        "CREATE SCHEMA IF NOT EXISTS dw;\n",
        encoding="utf-8",
    )
    write_create_file("02_create_clean_tables.sql", "clean", CLEAN_TABLES)
    write_create_file("03_create_analytics_tables.sql", "analytics", ANALYTICS_TABLES)
    write_create_file("04_create_dimensional_schema.sql", "dw", DIMENSIONAL_TABLES)
    (SQL_DIR / "05_create_indexes_and_constraints.sql").write_text(constraint_sql(), encoding="utf-8")
    write_copy_file("06_copy_clean_csv.sql", "clean", CLEAN_TABLES)
    write_copy_file("07_copy_analytics_csv.sql", "analytics", ANALYTICS_TABLES)
    write_copy_file("08_copy_dimensional_csv.sql", "dw", DIMENSIONAL_TABLES)
    (SQL_DIR / "09_validation_queries.sql").write_text(validation_sql(), encoding="utf-8")
    (SQL_DIR / "10_drop_all.sql").write_text(drop_sql(), encoding="utf-8")
    write_readme()
    print("SQL y README principal generados.")


if __name__ == "__main__":
    main()
