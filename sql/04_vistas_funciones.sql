-- =====================================================================
-- Data Mart Olist - Entregable 3
-- Script 04: vistas y funciones para el dashboard Streamlit
-- =====================================================================

SET search_path TO dw;

-- ---------------------------------------------------------------------
-- Vistas base
-- ---------------------------------------------------------------------

CREATE OR REPLACE VIEW vw_ventas_detalle AS
SELECT
    v.order_id,
    v.order_item_id,
    d.fecha,
    d.anio,
    d.mes,
    TO_CHAR(d.fecha, 'YYYY-MM') AS periodo,
    p.categoria_en AS categoria,
    s.seller_id,
    s.estado AS estado_vendedor,
    c.estado AS estado_cliente,
    e.order_status,
    v.price,
    v.freight_value,
    v.total_item,
    v.cantidad
FROM fact_ventas_items v
JOIN dim_fecha          d ON d.fecha_key    = v.fecha_compra_key
JOIN dim_producto       p ON p.producto_key = v.producto_key
JOIN dim_vendedor       s ON s.vendedor_key = v.vendedor_key
JOIN dim_cliente        c ON c.cliente_key  = v.cliente_key
JOIN dim_estado_pedido  e ON e.estado_key   = v.estado_key;

CREATE OR REPLACE VIEW vw_pedidos_detalle AS
SELECT
    fp.order_id,
    d.fecha AS fecha_compra,
    d.anio,
    d.mes,
    TO_CHAR(d.fecha, 'YYYY-MM') AS periodo,
    c.estado AS estado_cliente,
    c.ciudad AS ciudad_cliente,
    e.order_status,
    pg.tipo_pago,
    pg.rango_cuotas,
    fp.dias_entrega,
    fp.dias_retraso,
    fp.entrega_a_tiempo,
    fp.review_score,
    fp.payment_value_total,
    fp.num_items
FROM fact_pedidos fp
JOIN dim_fecha          d  ON d.fecha_key  = fp.fecha_compra_key
JOIN dim_cliente        c  ON c.cliente_key = fp.cliente_key
JOIN dim_estado_pedido  e  ON e.estado_key  = fp.estado_key
JOIN dim_pago           pg ON pg.pago_key   = fp.pago_key;

CREATE OR REPLACE VIEW vw_filtro_categorias AS
SELECT DISTINCT categoria_en AS categoria
FROM dim_producto
WHERE producto_key > 0 AND categoria_en IS NOT NULL
ORDER BY 1;

CREATE OR REPLACE VIEW vw_filtro_estados_cliente AS
SELECT DISTINCT estado
FROM dim_cliente
WHERE cliente_key > 0 AND estado IS NOT NULL AND estado <> 'XX'
ORDER BY 1;

-- ---------------------------------------------------------------------
-- Funciones de KPI y gráficos
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_kpi_ventas(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL
)
RETURNS TABLE (
    ingresos NUMERIC,
    flete NUMERIC,
    pedidos BIGINT,
    items BIGINT,
    ticket_promedio NUMERIC
)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        COALESCE(SUM(price), 0),
        COALESCE(SUM(freight_value), 0),
        COUNT(DISTINCT order_id),
        COUNT(*),
        COALESCE(ROUND(SUM(price) / NULLIF(COUNT(DISTINCT order_id), 0), 2), 0)
    FROM vw_ventas_detalle
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND (p_fecha_ini IS NULL OR fecha >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha <= p_fecha_fin)
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente);
$$;

CREATE OR REPLACE FUNCTION fn_ventas_por_mes(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL
)
RETURNS TABLE (periodo TEXT, ingresos NUMERIC, pedidos BIGINT)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        periodo,
        ROUND(SUM(price), 2) AS ingresos,
        COUNT(DISTINCT order_id) AS pedidos
    FROM vw_ventas_detalle
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND (p_fecha_ini IS NULL OR fecha >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha <= p_fecha_fin)
      AND (p_categoria IS NULL OR categoria = p_categoria)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente)
    GROUP BY periodo
    ORDER BY periodo;
$$;

CREATE OR REPLACE FUNCTION fn_top_categorias(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL,
    p_limite INT DEFAULT 8
)
RETURNS TABLE (categoria TEXT, ingresos NUMERIC, pct_total NUMERIC)
LANGUAGE sql STABLE SET search_path = dw AS $$
    WITH base AS (
        SELECT categoria, SUM(price) AS ingresos
        FROM vw_ventas_detalle
        WHERE order_status NOT IN ('canceled', 'unavailable')
          AND (p_fecha_ini IS NULL OR fecha >= p_fecha_ini)
          AND (p_fecha_fin IS NULL OR fecha <= p_fecha_fin)
          AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente)
        GROUP BY categoria
    ),
    tot AS (SELECT SUM(ingresos) AS total FROM base)
    SELECT
        b.categoria,
        ROUND(b.ingresos, 2),
        ROUND(100.0 * b.ingresos / NULLIF(t.total, 0), 1)
    FROM base b, tot t
    ORDER BY b.ingresos DESC
    LIMIT p_limite;
$$;

CREATE OR REPLACE FUNCTION fn_kpi_logistica(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL
)
RETURNS TABLE (
    pedidos_entregados BIGINT,
    pct_a_tiempo NUMERIC,
    dias_promedio NUMERIC
)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        COUNT(*),
        ROUND(100.0 * AVG(entrega_a_tiempo), 1),
        ROUND(AVG(dias_entrega), 1)
    FROM vw_pedidos_detalle
    WHERE order_status = 'delivered'
      AND (p_fecha_ini IS NULL OR fecha_compra >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha_compra <= p_fecha_fin)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente);
$$;

CREATE OR REPLACE FUNCTION fn_entrega_por_estado(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL
)
RETURNS TABLE (estado TEXT, pct_a_tiempo NUMERIC, dias_promedio NUMERIC, pedidos BIGINT)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        estado_cliente,
        ROUND(100.0 * AVG(entrega_a_tiempo), 1),
        ROUND(AVG(dias_entrega), 1),
        COUNT(*)
    FROM vw_pedidos_detalle
    WHERE order_status = 'delivered'
      AND (p_fecha_ini IS NULL OR fecha_compra >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha_compra <= p_fecha_fin)
    GROUP BY estado_cliente
    HAVING COUNT(*) >= 50
    ORDER BY 2 ASC;
$$;

CREATE OR REPLACE FUNCTION fn_kpi_satisfaccion(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL
)
RETURNS TABLE (
    resenas BIGINT,
    puntaje_promedio NUMERIC,
    pct_negativas NUMERIC
)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        COUNT(*) FILTER (WHERE review_score IS NOT NULL),
        ROUND(AVG(review_score) FILTER (WHERE review_score IS NOT NULL), 2),
        ROUND(100.0 * COUNT(*) FILTER (WHERE review_score IN (1, 2))
              / NULLIF(COUNT(*) FILTER (WHERE review_score IS NOT NULL), 0), 1)
    FROM vw_pedidos_detalle
    WHERE order_status = 'delivered'
      AND (p_fecha_ini IS NULL OR fecha_compra >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha_compra <= p_fecha_fin)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente);
$$;

CREATE OR REPLACE FUNCTION fn_satisfaccion_vs_entrega(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL
)
RETURNS TABLE (tipo_entrega TEXT, puntaje_promedio NUMERIC, pedidos BIGINT)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        CASE WHEN entrega_a_tiempo = 1 THEN 'A tiempo'
             WHEN entrega_a_tiempo = 0 THEN 'Tardia'
             ELSE 'Sin dato' END,
        ROUND(AVG(review_score), 2),
        COUNT(*)
    FROM vw_pedidos_detalle
    WHERE order_status = 'delivered'
      AND review_score IS NOT NULL
      AND entrega_a_tiempo IS NOT NULL
      AND (p_fecha_ini IS NULL OR fecha_compra >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha_compra <= p_fecha_fin)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente)
    GROUP BY 1
    ORDER BY 1;
$$;

CREATE OR REPLACE FUNCTION fn_top_vendedores(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL,
    p_limite INT DEFAULT 10
)
RETURNS TABLE (seller_id TEXT, ingresos NUMERIC, pedidos BIGINT, pct_total NUMERIC)
LANGUAGE sql STABLE SET search_path = dw AS $$
    WITH base AS (
        SELECT seller_id, SUM(price) AS ingresos, COUNT(DISTINCT order_id) AS pedidos
        FROM vw_ventas_detalle
        WHERE order_status NOT IN ('canceled', 'unavailable')
          AND (p_fecha_ini IS NULL OR fecha >= p_fecha_ini)
          AND (p_fecha_fin IS NULL OR fecha <= p_fecha_fin)
          AND (p_categoria IS NULL OR categoria = p_categoria)
        GROUP BY seller_id
    ),
    tot AS (SELECT SUM(ingresos) AS total FROM base)
    SELECT
        b.seller_id,
        ROUND(b.ingresos, 2),
        b.pedidos,
        ROUND(100.0 * b.ingresos / NULLIF(t.total, 0), 1)
    FROM base b, tot t
    ORDER BY b.ingresos DESC
    LIMIT p_limite;
$$;

CREATE OR REPLACE FUNCTION fn_concentracion_vendedores(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_categoria TEXT DEFAULT NULL
)
RETURNS TABLE (
    vendedores_activos BIGINT,
    pct_ingresos_top10 NUMERIC,
    ingresos_lider NUMERIC
)
LANGUAGE sql STABLE SET search_path = dw AS $$
    WITH base AS (
        SELECT seller_id, SUM(price) AS ingresos
        FROM vw_ventas_detalle
        WHERE order_status NOT IN ('canceled', 'unavailable')
          AND (p_fecha_ini IS NULL OR fecha >= p_fecha_ini)
          AND (p_fecha_fin IS NULL OR fecha <= p_fecha_fin)
          AND (p_categoria IS NULL OR categoria = p_categoria)
        GROUP BY seller_id
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER (ORDER BY ingresos DESC) AS rn,
               COUNT(*) OVER () AS total_vend
        FROM base
    ),
    top10 AS (
        SELECT SUM(ingresos) AS ingresos_top
        FROM ranked
        WHERE rn <= CEIL(total_vend * 0.10)
    ),
    tot AS (SELECT SUM(ingresos) AS total, MAX(ingresos) AS lider FROM base)
    SELECT
        (SELECT COUNT(*) FROM base),
        ROUND(100.0 * t10.ingresos_top / NULLIF(t.total, 0), 1),
        ROUND(t.lider, 2)
    FROM top10 t10, tot t;
$$;

CREATE OR REPLACE FUNCTION fn_detalle_pedidos(
    p_fecha_ini DATE DEFAULT NULL,
    p_fecha_fin DATE DEFAULT NULL,
    p_estado_cliente TEXT DEFAULT NULL,
    p_limite INT DEFAULT 100
)
RETURNS TABLE (
    order_id TEXT,
    fecha_compra DATE,
    estado_cliente TEXT,
    order_status TEXT,
    dias_entrega INT,
    entrega_a_tiempo SMALLINT,
    review_score SMALLINT,
    payment_value_total NUMERIC,
    num_items SMALLINT
)
LANGUAGE sql STABLE SET search_path = dw AS $$
    SELECT
        order_id,
        fecha_compra,
        estado_cliente,
        order_status,
        dias_entrega,
        entrega_a_tiempo,
        review_score,
        payment_value_total,
        num_items
    FROM vw_pedidos_detalle
    WHERE (p_fecha_ini IS NULL OR fecha_compra >= p_fecha_ini)
      AND (p_fecha_fin IS NULL OR fecha_compra <= p_fecha_fin)
      AND (p_estado_cliente IS NULL OR estado_cliente = p_estado_cliente)
    ORDER BY fecha_compra DESC
    LIMIT p_limite;
$$;
