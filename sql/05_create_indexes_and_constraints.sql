-- Llaves, restricciones e indices principales.

ALTER TABLE analytics.pobreza_alcaldia_anio ADD CONSTRAINT pk_pobreza_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
ALTER TABLE analytics.infraestructura_alcaldia ADD CONSTRAINT pk_infraestructura_alcaldia PRIMARY KEY (alcaldia_key);
ALTER TABLE analytics.delitos_alcaldia_mes_subtipo ADD CONSTRAINT pk_delitos_mes_subtipo PRIMARY KEY (alcaldia_key, anio, mes, subtipo_robo_patrimonial);
ALTER TABLE analytics.delitos_alcaldia_anio ADD CONSTRAINT pk_delitos_alcaldia_anio PRIMARY KEY (alcaldia_key, anio);
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

ALTER TABLE dw.fact_delitos_alcaldia_mes_subtipo ADD CONSTRAINT pk_fact_delitos_mes_subtipo PRIMARY KEY (alcaldia_id, tiempo_id, delito_subtipo_id);
ALTER TABLE dw.fact_delitos_alcaldia_anio ADD CONSTRAINT pk_fact_delitos_anio PRIMARY KEY (alcaldia_id, tiempo_id);
ALTER TABLE dw.fact_pobreza_alcaldia_anio ADD CONSTRAINT pk_fact_pobreza_anio PRIMARY KEY (alcaldia_id, tiempo_id);
ALTER TABLE dw.fact_infraestructura_alcaldia ADD CONSTRAINT pk_fact_infra_alcaldia PRIMARY KEY (alcaldia_id, snapshot_tiempo_id);
ALTER TABLE dw.fact_infraestructura_colonia ADD CONSTRAINT pk_fact_infra_colonia PRIMARY KEY (colonia_id, snapshot_tiempo_id);
ALTER TABLE dw.fact_panel_analitico_alcaldia_anio ADD CONSTRAINT pk_fact_panel PRIMARY KEY (alcaldia_id, tiempo_id);

ALTER TABLE dw.dim_colonia ADD CONSTRAINT fk_dim_colonia_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);

ALTER TABLE dw.fact_delitos_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_delitos_mes_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_delitos_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_delitos_mes_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_delitos_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_delitos_mes_subtipo FOREIGN KEY (delito_subtipo_id) REFERENCES dw.dim_delito_subtipo(delito_subtipo_id);
ALTER TABLE dw.fact_delitos_alcaldia_mes_subtipo ADD CONSTRAINT fk_fact_delitos_mes_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

ALTER TABLE dw.fact_delitos_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_anio_alcaldia FOREIGN KEY (alcaldia_id) REFERENCES dw.dim_alcaldia(alcaldia_id);
ALTER TABLE dw.fact_delitos_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_anio_tiempo FOREIGN KEY (tiempo_id) REFERENCES dw.dim_tiempo(tiempo_id);
ALTER TABLE dw.fact_delitos_alcaldia_anio ADD CONSTRAINT fk_fact_delitos_anio_fuente FOREIGN KEY (fuente_datos_id) REFERENCES dw.dim_fuente_datos(fuente_datos_id);

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
CREATE INDEX IF NOT EXISTS idx_dw_fact_delitos_mes_alcaldia_tiempo ON dw.fact_delitos_alcaldia_mes_subtipo (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_delitos_mes_subtipo ON dw.fact_delitos_alcaldia_mes_subtipo (delito_subtipo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_delitos_anio_alcaldia_tiempo ON dw.fact_delitos_alcaldia_anio (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_pobreza_alcaldia_tiempo ON dw.fact_pobreza_alcaldia_anio (alcaldia_id, tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_infra_alcaldia_snapshot ON dw.fact_infraestructura_alcaldia (alcaldia_id, snapshot_tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_infra_colonia_snapshot ON dw.fact_infraestructura_colonia (alcaldia_id, snapshot_tiempo_id);
CREATE INDEX IF NOT EXISTS idx_dw_fact_panel_alcaldia_tiempo ON dw.fact_panel_analitico_alcaldia_anio (alcaldia_id, tiempo_id);
