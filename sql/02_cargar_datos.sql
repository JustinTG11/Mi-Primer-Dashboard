-- =====================================================================
-- Data Mart Olist - Entregable 3
-- Script 02: carga de datos (los CSV están montados en /data)
-- Orden: primero dimensiones y luego hechos, por las claves foráneas.
-- =====================================================================

SET search_path TO dw;

COPY dim_fecha         FROM '/data/dim_fecha.csv'         WITH (FORMAT csv, HEADER true, NULL '');
COPY dim_cliente       FROM '/data/dim_cliente.csv'       WITH (FORMAT csv, HEADER true, NULL '');
COPY dim_producto      FROM '/data/dim_producto.csv'      WITH (FORMAT csv, HEADER true, NULL '');
COPY dim_vendedor      FROM '/data/dim_vendedor.csv'      WITH (FORMAT csv, HEADER true, NULL '');
COPY dim_estado_pedido FROM '/data/dim_estado_pedido.csv' WITH (FORMAT csv, HEADER true, NULL '');
COPY dim_pago          FROM '/data/dim_pago.csv'          WITH (FORMAT csv, HEADER true, NULL '');
COPY fact_pedidos      FROM '/data/fact_pedidos.csv'      WITH (FORMAT csv, HEADER true, NULL '');
COPY fact_ventas_items FROM '/data/fact_ventas_items.csv' WITH (FORMAT csv, HEADER true, NULL '');

ANALYZE;
