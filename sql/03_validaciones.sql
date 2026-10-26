-- =====================================================================
-- Data Mart Olist - Entregable 3
-- Script 03: consultas de validación
-- =====================================================================

SET search_path TO dw;

-- 7.1 Cantidad de registros
SELECT 'dim_fecha' AS tabla, COUNT(*) AS filas, 822 AS esperado,
       CASE WHEN COUNT(*) = 822 THEN 'OK' ELSE 'REVISAR' END AS estado FROM dim_fecha
UNION ALL
SELECT 'dim_cliente', COUNT(*), 96097, CASE WHEN COUNT(*) = 96097 THEN 'OK' ELSE 'REVISAR' END FROM dim_cliente
UNION ALL
SELECT 'dim_producto', COUNT(*), 32952, CASE WHEN COUNT(*) = 32952 THEN 'OK' ELSE 'REVISAR' END FROM dim_producto
UNION ALL
SELECT 'dim_vendedor', COUNT(*), 3096, CASE WHEN COUNT(*) = 3096 THEN 'OK' ELSE 'REVISAR' END FROM dim_vendedor
UNION ALL
SELECT 'dim_estado_pedido', COUNT(*), 9, CASE WHEN COUNT(*) = 9 THEN 'OK' ELSE 'REVISAR' END FROM dim_estado_pedido
UNION ALL
SELECT 'dim_pago', COUNT(*), (SELECT COUNT(*) FROM dim_pago), 'OK' FROM dim_pago
UNION ALL
SELECT 'fact_pedidos', COUNT(*), 99441, CASE WHEN COUNT(*) = 99441 THEN 'OK' ELSE 'REVISAR' END FROM fact_pedidos
UNION ALL
SELECT 'fact_ventas_items', COUNT(*), 112650, CASE WHEN COUNT(*) = 112650 THEN 'OK' ELSE 'REVISAR' END FROM fact_ventas_items;

-- 7.2 Integridad de relaciones (huérfanos)
SELECT 'fact_pedidos -> dim_fecha (compra)' AS relacion,
       COUNT(*) AS huerfanos,
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END AS estado
FROM fact_pedidos fp LEFT JOIN dim_fecha d ON d.fecha_key = fp.fecha_compra_key
WHERE d.fecha_key IS NULL
UNION ALL
SELECT 'fact_pedidos -> dim_cliente', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_pedidos fp LEFT JOIN dim_cliente c ON c.cliente_key = fp.cliente_key
WHERE c.cliente_key IS NULL
UNION ALL
SELECT 'fact_pedidos -> dim_estado', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_pedidos fp LEFT JOIN dim_estado_pedido e ON e.estado_key = fp.estado_key
WHERE e.estado_key IS NULL
UNION ALL
SELECT 'fact_pedidos -> dim_pago', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_pedidos fp LEFT JOIN dim_pago p ON p.pago_key = fp.pago_key
WHERE p.pago_key IS NULL
UNION ALL
SELECT 'fact_ventas_items -> fact_pedidos', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_ventas_items v LEFT JOIN fact_pedidos fp ON fp.order_id = v.order_id
WHERE fp.order_id IS NULL
UNION ALL
SELECT 'fact_ventas_items -> dim_producto', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_ventas_items v LEFT JOIN dim_producto p ON p.producto_key = v.producto_key
WHERE p.producto_key IS NULL
UNION ALL
SELECT 'fact_ventas_items -> dim_vendedor', COUNT(*),
       CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'REVISAR' END
FROM fact_ventas_items v LEFT JOIN dim_vendedor s ON s.vendedor_key = v.vendedor_key
WHERE s.vendedor_key IS NULL;

-- 7.3 Valores nulos relevantes
SELECT 'Pedidos sin reseña' AS indicador, COUNT(*) AS cantidad
FROM fact_pedidos WHERE review_score IS NULL
UNION ALL
SELECT 'Pedidos sin fecha de entrega', COUNT(*)
FROM fact_pedidos WHERE dias_entrega IS NULL
UNION ALL
SELECT 'Pedidos delivered sin fecha de entrega', COUNT(*)
FROM fact_pedidos fp
JOIN dim_estado_pedido e ON e.estado_key = fp.estado_key
WHERE e.order_status = 'delivered' AND fp.dias_entrega IS NULL
UNION ALL
SELECT 'Pedidos sin pago (pago_key=0)', COUNT(*)
FROM fact_pedidos WHERE pago_key = 0
UNION ALL
SELECT 'Pedidos sin ítems', COUNT(*)
FROM fact_pedidos WHERE num_items = 0
UNION ALL
SELECT 'Productos sin categoría (sin_categoria)', COUNT(*)
FROM dim_producto WHERE categoria_en = 'no_category' AND producto_key > 0;

-- 7.4 Totales principales
SELECT
    ROUND(SUM(price)::numeric, 2) AS ingresos_totales,
    ROUND(SUM(freight_value)::numeric, 2) AS flete_total,
    COUNT(DISTINCT order_id) AS pedidos_con_items
FROM fact_ventas_items;

SELECT
    COUNT(*) FILTER (WHERE e.order_status = 'delivered') AS pedidos_entregados,
    ROUND(100.0 * AVG(entrega_a_tiempo) FILTER (WHERE e.order_status = 'delivered'), 1) AS pct_a_tiempo,
    ROUND(AVG(dias_entrega) FILTER (WHERE e.order_status = 'delivered'), 1) AS dias_promedio,
    ROUND(AVG(review_score) FILTER (WHERE review_score IS NOT NULL), 2) AS puntaje_promedio
FROM fact_pedidos fp
JOIN dim_estado_pedido e ON e.estado_key = fp.estado_key;
