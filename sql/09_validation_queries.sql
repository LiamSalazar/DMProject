-- Consultas de validacion posteriores a la carga.

SELECT 'dw.dim_alcaldia_count' AS check_name, COUNT(*) AS value FROM dw.dim_alcaldia;
SELECT 'panel_rows' AS check_name, COUNT(*) AS value FROM analytics.panel_alcaldia_anio;
SELECT anio, COUNT(DISTINCT alcaldia_key) AS alcaldias FROM analytics.panel_alcaldia_anio GROUP BY anio ORDER BY anio;
SELECT COUNT(*) AS infra_snapshot_rows FROM dw.fact_infraestructura_alcaldia WHERE snapshot_tiempo_id = 202200 AND infraestructura_actualizacion_anio = 2022 AND infraestructura_es_snapshot IS TRUE;
SELECT COUNT(*) AS facts_without_alcaldia
FROM dw.fact_panel_analitico_alcaldia_anio f
LEFT JOIN dw.dim_alcaldia d ON d.alcaldia_id = f.alcaldia_id
WHERE d.alcaldia_id IS NULL;
SELECT COUNT(*) AS facts_without_tiempo
FROM dw.fact_panel_analitico_alcaldia_anio f
LEFT JOIN dw.dim_tiempo d ON d.tiempo_id = f.tiempo_id
WHERE d.tiempo_id IS NULL;
SELECT feature_role, COUNT(*) FROM analytics.feature_catalog GROUP BY feature_role ORDER BY feature_role;
