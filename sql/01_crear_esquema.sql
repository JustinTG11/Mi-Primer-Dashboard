-- =====================================================================
-- Data Mart Olist - Entregable 3
-- Script 01: creación del esquema, dimensiones y tablas de hechos
-- Motor: PostgreSQL 17
-- =====================================================================

DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;
SET search_path TO dw;

-- ---------------------------------------------------------------------
-- DIMENSIONES (la fila con clave 0 representa "sin dato")
-- ---------------------------------------------------------------------

CREATE TABLE dim_fecha (
    fecha_key        INTEGER      PRIMARY KEY,          -- formato AAAAMMDD (0 = sin dato)
    fecha            DATE,
    dia              SMALLINT,
    mes              SMALLINT,
    nombre_mes       VARCHAR(15)  NOT NULL,
    trimestre        SMALLINT,
    anio             SMALLINT,
    dia_semana       SMALLINT,                          -- 1 = lunes ... 7 = domingo
    nombre_dia       VARCHAR(15)  NOT NULL,
    es_fin_de_semana BOOLEAN
);

CREATE TABLE dim_cliente (
    cliente_key        INTEGER      PRIMARY KEY,
    customer_unique_id VARCHAR(32)  NOT NULL UNIQUE,
    ciudad             VARCHAR(100),
    estado             VARCHAR(2),
    prefijo_postal     VARCHAR(5)
);

CREATE TABLE dim_producto (
    producto_key INTEGER      PRIMARY KEY,
    product_id   VARCHAR(32)  NOT NULL UNIQUE,
    categoria_pt VARCHAR(100) NOT NULL,
    categoria_en VARCHAR(100) NOT NULL,
    peso_g       INTEGER,
    largo_cm     INTEGER,
    alto_cm      INTEGER,
    ancho_cm     INTEGER
);

CREATE TABLE dim_vendedor (
    vendedor_key INTEGER      PRIMARY KEY,
    seller_id    VARCHAR(32)  NOT NULL UNIQUE,
    ciudad       VARCHAR(100),
    estado       VARCHAR(2)
);

CREATE TABLE dim_estado_pedido (
    estado_key   INTEGER      PRIMARY KEY,
    order_status VARCHAR(20)  NOT NULL UNIQUE
);

CREATE TABLE dim_pago (
    pago_key     INTEGER      PRIMARY KEY,
    tipo_pago    VARCHAR(20)  NOT NULL,
    rango_cuotas VARCHAR(20)  NOT NULL,
    UNIQUE (tipo_pago, rango_cuotas)
);

-- ---------------------------------------------------------------------
-- TABLAS DE HECHOS
-- ---------------------------------------------------------------------

-- Granularidad: una fila = un pedido realizado por un cliente.
CREATE TABLE fact_pedidos (
    order_id            VARCHAR(32)   PRIMARY KEY,
    fecha_compra_key    INTEGER       NOT NULL REFERENCES dim_fecha (fecha_key),
    fecha_entrega_key   INTEGER       NOT NULL REFERENCES dim_fecha (fecha_key),
    fecha_estimada_key  INTEGER       NOT NULL REFERENCES dim_fecha (fecha_key),
    cliente_key         INTEGER       NOT NULL REFERENCES dim_cliente (cliente_key),
    estado_key          INTEGER       NOT NULL REFERENCES dim_estado_pedido (estado_key),
    pago_key            INTEGER       NOT NULL REFERENCES dim_pago (pago_key),
    dias_entrega        INTEGER,                         -- NULL si no hay entrega
    dias_retraso        INTEGER,                         -- > 0 = entrega tardía
    entrega_a_tiempo    SMALLINT      CHECK (entrega_a_tiempo IS NULL OR entrega_a_tiempo IN (0, 1)),
    review_score        SMALLINT      CHECK (review_score IS NULL OR review_score BETWEEN 1 AND 5),
    payment_value_total NUMERIC(12,2),
    num_items           SMALLINT      NOT NULL DEFAULT 0,
    cantidad_pedidos    SMALLINT      NOT NULL DEFAULT 1
);

-- Granularidad: una fila = un ítem (producto) vendido dentro de un pedido,
-- por un vendedor, en la fecha de compra del pedido.
CREATE TABLE fact_ventas_items (
    order_id         VARCHAR(32)   NOT NULL REFERENCES fact_pedidos (order_id),
    order_item_id    SMALLINT      NOT NULL,
    fecha_compra_key INTEGER       NOT NULL REFERENCES dim_fecha (fecha_key),
    cliente_key      INTEGER       NOT NULL REFERENCES dim_cliente (cliente_key),
    producto_key     INTEGER       NOT NULL REFERENCES dim_producto (producto_key),
    vendedor_key     INTEGER       NOT NULL REFERENCES dim_vendedor (vendedor_key),
    estado_key       INTEGER       NOT NULL REFERENCES dim_estado_pedido (estado_key),
    price            NUMERIC(10,2) NOT NULL,
    freight_value    NUMERIC(10,2) NOT NULL,
    total_item       NUMERIC(10,2) NOT NULL,
    cantidad         SMALLINT      NOT NULL DEFAULT 1,
    PRIMARY KEY (order_id, order_item_id)
);

-- ---------------------------------------------------------------------
-- ÍNDICES sobre las claves foráneas
-- ---------------------------------------------------------------------
CREATE INDEX ix_fp_fecha_compra ON fact_pedidos (fecha_compra_key);
CREATE INDEX ix_fp_cliente      ON fact_pedidos (cliente_key);
CREATE INDEX ix_fp_estado       ON fact_pedidos (estado_key);
CREATE INDEX ix_fp_pago         ON fact_pedidos (pago_key);
CREATE INDEX ix_fv_fecha        ON fact_ventas_items (fecha_compra_key);
CREATE INDEX ix_fv_cliente      ON fact_ventas_items (cliente_key);
CREATE INDEX ix_fv_producto     ON fact_ventas_items (producto_key);
CREATE INDEX ix_fv_vendedor     ON fact_ventas_items (vendedor_key);
CREATE INDEX ix_fv_estado       ON fact_ventas_items (estado_key);
