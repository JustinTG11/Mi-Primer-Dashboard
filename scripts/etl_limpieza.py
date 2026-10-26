#!/usr/bin/env python3
"""
ETL de limpieza y transformación - Brazilian E-Commerce Public Dataset by Olist
Entregable 3 - MI PRIMER DASHBOARD
Genera las 8 tablas del Data Mart dimensional (esquema dw).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import unicodedata
import warnings
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "raw_data"
CLEAN = BASE / "clean"
CLEAN.mkdir(exist_ok=True)
LOG_FILE = BASE / "scripts" / "transformaciones_log.txt"

log_lines = []

def log(msg: str):
    print(msg)
    log_lines.append(f"[{datetime.now():%H:%M:%S}] {msg}")


def strip_accents(text: str) -> str:
    if pd.isna(text):
        return text
    text = str(text).lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# 1. Carga de datos originales
# ---------------------------------------------------------------------------
log("=" * 60)
log("1. Cargando datasets originales...")

orders = pd.read_csv(RAW / "olist_orders_dataset.csv")
items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
payments = pd.read_csv(RAW / "olist_order_payments_dataset.csv")
reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
products = pd.read_csv(RAW / "olist_products_dataset.csv")
sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
translation = pd.read_csv(RAW / "product_category_name_translation.csv")

log(f"  orders: {len(orders):,} | items: {len(items):,} | payments: {len(payments):,}")
log(f"  reviews: {len(reviews):,} | customers: {len(customers):,} | products: {len(products):,}")
log(f"  sellers: {len(sellers):,} | translation: {len(translation):,}")

# ---------------------------------------------------------------------------
# 2. Conversión de fechas
# ---------------------------------------------------------------------------
log("2. Convirtiendo fechas...")
date_cols = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
for col in date_cols:
    orders[col] = pd.to_datetime(orders[col], errors="coerce")

items["shipping_limit_date"] = pd.to_datetime(items["shipping_limit_date"], errors="coerce")
reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"], errors="coerce")
reviews["review_answer_timestamp"] = pd.to_datetime(reviews["review_answer_timestamp"], errors="coerce")

# ---------------------------------------------------------------------------
# 3. Clientes: consolidar por customer_unique_id (ubicación del pedido más reciente)
# ---------------------------------------------------------------------------
log("3. Consolidando clientes por customer_unique_id...")
cust = customers.copy()
cust["ciudad"] = cust["customer_city"].apply(strip_accents)
cust["estado"] = cust["customer_state"].str.upper().str.strip()
cust["prefijo_postal"] = cust["customer_zip_code_prefix"].astype(str).str.zfill(5)

# Unir con fecha de compra para quedarnos con la ubicación del pedido más reciente
cust = cust.merge(
    orders[["customer_id", "order_purchase_timestamp"]],
    on="customer_id",
    how="left",
)
cust = cust.sort_values("order_purchase_timestamp", ascending=False)
cust = cust.drop_duplicates(subset=["customer_unique_id"], keep="first")
cust = cust[["customer_unique_id", "ciudad", "estado", "prefijo_postal"]].reset_index(drop=True)

# Clave sustituta + fila 0
cust.insert(0, "cliente_key", range(1, len(cust) + 1))
sin_dato_cli = pd.DataFrame(
    [{"cliente_key": 0, "customer_unique_id": "SIN_DATO", "ciudad": "sin_dato", "estado": "XX", "prefijo_postal": "00000"}]
)
dim_cliente = pd.concat([sin_dato_cli, cust], ignore_index=True)
log(f"  dim_cliente: {len(dim_cliente):,} filas (incluye clave 0)")

# Mapa customer_id original -> customer_unique_id (para hechos)
cust_map = customers[["customer_id", "customer_unique_id"]].drop_duplicates()
cust_key_map = dim_cliente.set_index("customer_unique_id")["cliente_key"].to_dict()

# ---------------------------------------------------------------------------
# 4. Productos + traducción
# ---------------------------------------------------------------------------
log("4. Preparando productos...")
prod = products.copy()
# Renombrar columnas con typo
prod = prod.rename(columns={
    "product_name_lenght": "product_name_length",
    "product_description_lenght": "product_description_length",
})
# Categoría nula -> sin_categoria
prod["product_category_name"] = prod["product_category_name"].fillna("sin_categoria")

# Traducciones faltantes
extra_trans = pd.DataFrame([
    {"product_category_name": "pc_gamer", "product_category_name_english": "pc_gamer"},
    {"product_category_name": "portateis_cozinha_e_preparadores_de_alimentos",
     "product_category_name_english": "kitchen_portable_and_food_preparers"},
    {"product_category_name": "sin_categoria", "product_category_name_english": "no_category"},
])
translation = pd.concat([translation, extra_trans], ignore_index=True)
translation = translation.drop_duplicates(subset=["product_category_name"], keep="first")

prod = prod.merge(translation, on="product_category_name", how="left")
prod["product_category_name_english"] = prod["product_category_name_english"].fillna(prod["product_category_name"])

dim_producto = prod[[
    "product_id",
    "product_category_name",
    "product_category_name_english",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]].copy()
dim_producto.columns = [
    "product_id", "categoria_pt", "categoria_en",
    "peso_g", "largo_cm", "alto_cm", "ancho_cm",
]
# Tipos enteros
for c in ["peso_g", "largo_cm", "alto_cm", "ancho_cm"]:
    dim_producto[c] = pd.to_numeric(dim_producto[c], errors="coerce").astype("Int64")

dim_producto.insert(0, "producto_key", range(1, len(dim_producto) + 1))
sin_dato_prod = pd.DataFrame([{
    "producto_key": 0, "product_id": "SIN_DATO",
    "categoria_pt": "sin_categoria", "categoria_en": "no_category",
    "peso_g": None, "largo_cm": None, "alto_cm": None, "ancho_cm": None,
}])
dim_producto = pd.concat([sin_dato_prod, dim_producto], ignore_index=True)
log(f"  dim_producto: {len(dim_producto):,} filas")

prod_key_map = dim_producto.set_index("product_id")["producto_key"].to_dict()

# ---------------------------------------------------------------------------
# 5. Vendedores
# ---------------------------------------------------------------------------
log("5. Preparando vendedores...")
sel = sellers.copy()
sel["ciudad"] = sel["seller_city"].apply(strip_accents)
sel["estado"] = sel["seller_state"].str.upper().str.strip()
dim_vendedor = sel[["seller_id", "ciudad", "estado"]].copy()
dim_vendedor.insert(0, "vendedor_key", range(1, len(dim_vendedor) + 1))
sin_dato_sel = pd.DataFrame([{"vendedor_key": 0, "seller_id": "SIN_DATO", "ciudad": "sin_dato", "estado": "XX"}])
dim_vendedor = pd.concat([sin_dato_sel, dim_vendedor], ignore_index=True)
log(f"  dim_vendedor: {len(dim_vendedor):,} filas")

vend_key_map = dim_vendedor.set_index("seller_id")["vendedor_key"].to_dict()

# ---------------------------------------------------------------------------
# 6. Estado del pedido
# ---------------------------------------------------------------------------
log("6. Preparando estados de pedido...")
estados = sorted(orders["order_status"].dropna().unique())
dim_estado = pd.DataFrame({"order_status": estados})
dim_estado.insert(0, "estado_key", range(1, len(dim_estado) + 1))
sin_dato_est = pd.DataFrame([{"estado_key": 0, "order_status": "sin_dato"}])
dim_estado = pd.concat([sin_dato_est, dim_estado], ignore_index=True)
log(f"  dim_estado_pedido: {len(dim_estado):,} filas")

estado_key_map = dim_estado.set_index("order_status")["estado_key"].to_dict()

# ---------------------------------------------------------------------------
# 7. Pagos: pago principal por pedido + rangos de cuotas
# ---------------------------------------------------------------------------
log("7. Preparando pagos...")
pay = payments.copy()
pay["payment_type"] = pay["payment_type"].replace({"not_defined": "otro"})
pay.loc[pay["payment_installments"] == 0, "payment_installments"] = 1

def rango_cuotas(n):
    if pd.isna(n):
        return "sin_dato"
    n = int(n)
    if n == 1:
        return "1 cuota"
    if n <= 3:
        return "2-3 cuotas"
    if n <= 6:
        return "4-6 cuotas"
    if n <= 12:
        return "7-12 cuotas"
    return "13+ cuotas"

pay["rango_cuotas"] = pay["payment_installments"].apply(rango_cuotas)

# Pago principal = el de mayor valor por pedido
pay_main = (
    pay.sort_values("payment_value", ascending=False)
    .drop_duplicates(subset=["order_id"], keep="first")
    [["order_id", "payment_type", "rango_cuotas", "payment_value"]]
)

# Total de pagos por pedido
pay_total = pay.groupby("order_id", as_index=False)["payment_value"].sum()
pay_total = pay_total.rename(columns={"payment_value": "payment_value_total"})

# Dimensión de pago (combinaciones únicas)
dim_pago = pay_main[["payment_type", "rango_cuotas"]].drop_duplicates().reset_index(drop=True)
dim_pago.insert(0, "pago_key", range(1, len(dim_pago) + 1))
sin_dato_pago = pd.DataFrame([{"pago_key": 0, "payment_type": "sin_dato", "rango_cuotas": "sin_dato"}])
dim_pago = pd.concat([sin_dato_pago, dim_pago], ignore_index=True)
dim_pago = dim_pago.rename(columns={"payment_type": "tipo_pago"})
log(f"  dim_pago: {len(dim_pago):,} filas")

pago_key_map = dim_pago.set_index(["tipo_pago", "rango_cuotas"])["pago_key"].to_dict()

# ---------------------------------------------------------------------------
# 8. Reseñas: una sola por pedido (la más reciente)
# ---------------------------------------------------------------------------
log("8. Preparando reseñas (una por pedido)...")
rev = reviews.copy()
rev = rev.sort_values("review_answer_timestamp", ascending=False)
rev = rev.drop_duplicates(subset=["order_id"], keep="first")
rev = rev[["order_id", "review_score"]].copy()
log(f"  reseñas únicas por pedido: {len(rev):,}")

# ---------------------------------------------------------------------------
# 9. Dimensión fecha (calendario continuo)
# ---------------------------------------------------------------------------
log("9. Generando dimensión fecha...")
min_date = orders["order_purchase_timestamp"].min().normalize()
max_date = max(
    orders["order_purchase_timestamp"].max(),
    orders["order_delivered_customer_date"].max(skipna=True),
    orders["order_estimated_delivery_date"].max(skipna=True),
).normalize()

# Ampliar un poco el rango
min_date = pd.Timestamp("2016-09-01")
max_date = pd.Timestamp("2018-11-30")

fechas = pd.date_range(min_date, max_date, freq="D")
dim_fecha = pd.DataFrame({"fecha": fechas})
dim_fecha["fecha_key"] = dim_fecha["fecha"].dt.strftime("%Y%m%d").astype(int)
dim_fecha["dia"] = dim_fecha["fecha"].dt.day
dim_fecha["mes"] = dim_fecha["fecha"].dt.month
dim_fecha["nombre_mes"] = dim_fecha["fecha"].dt.strftime("%B")
dim_fecha["trimestre"] = dim_fecha["fecha"].dt.quarter
dim_fecha["anio"] = dim_fecha["fecha"].dt.year
dim_fecha["dia_semana"] = dim_fecha["fecha"].dt.dayofweek + 1  # 1=lunes
dim_fecha["nombre_dia"] = dim_fecha["fecha"].dt.strftime("%A")
dim_fecha["es_fin_de_semana"] = dim_fecha["dia_semana"].isin([6, 7])

# Traducir nombres al español
meses_es = {
    "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
    "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
    "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre",
}
dias_es = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
}
dim_fecha["nombre_mes"] = dim_fecha["nombre_mes"].map(meses_es)
dim_fecha["nombre_dia"] = dim_fecha["nombre_dia"].map(dias_es)

sin_dato_fecha = pd.DataFrame([{
    "fecha_key": 0, "fecha": None, "dia": None, "mes": None,
    "nombre_mes": "sin_dato", "trimestre": None, "anio": None,
    "dia_semana": None, "nombre_dia": "sin_dato", "es_fin_de_semana": None,
}])
dim_fecha = pd.concat([sin_dato_fecha, dim_fecha], ignore_index=True)
dim_fecha = dim_fecha[[
    "fecha_key", "fecha", "dia", "mes", "nombre_mes", "trimestre",
    "anio", "dia_semana", "nombre_dia", "es_fin_de_semana",
]]
log(f"  dim_fecha: {len(dim_fecha):,} filas")

def to_fecha_key(ts):
    if pd.isna(ts):
        return 0
    return int(pd.Timestamp(ts).strftime("%Y%m%d"))

# ---------------------------------------------------------------------------
# 10. fact_pedidos
# ---------------------------------------------------------------------------
log("10. Construyendo fact_pedidos...")
fp = orders.copy()

# cliente_key
fp = fp.merge(cust_map, on="customer_id", how="left")
fp["cliente_key"] = fp["customer_unique_id"].map(cust_key_map).fillna(0).astype(int)

# estado_key
fp["estado_key"] = fp["order_status"].map(estado_key_map).fillna(0).astype(int)

# fechas
fp["fecha_compra_key"] = fp["order_purchase_timestamp"].apply(to_fecha_key)
fp["fecha_entrega_key"] = fp["order_delivered_customer_date"].apply(to_fecha_key)
fp["fecha_estimada_key"] = fp["order_estimated_delivery_date"].apply(to_fecha_key)

# Medidas de entrega (solo fechas, sin hora)
fp["fecha_compra"] = fp["order_purchase_timestamp"].dt.normalize()
fp["fecha_entrega"] = fp["order_delivered_customer_date"].dt.normalize()
fp["fecha_estimada"] = fp["order_estimated_delivery_date"].dt.normalize()

fp["dias_entrega"] = (fp["fecha_entrega"] - fp["fecha_compra"]).dt.days
fp["dias_retraso"] = (fp["fecha_entrega"] - fp["fecha_estimada"]).dt.days
# entrega_a_tiempo: 1 si entrega real <= estimada, 0 si > , NULL si no hay entrega
fp["entrega_a_tiempo"] = np.where(
    fp["fecha_entrega"].notna() & fp["fecha_estimada"].notna(),
    (fp["fecha_entrega"] <= fp["fecha_estimada"]).astype(int),
    np.nan,
)
fp["entrega_a_tiempo"] = fp["entrega_a_tiempo"].astype("Int64")

# Reseña
fp = fp.merge(rev, on="order_id", how="left")
fp["review_score"] = fp["review_score"].astype("Int64")

# Pago
fp = fp.merge(pay_main[["order_id", "payment_type", "rango_cuotas"]], on="order_id", how="left")
fp = fp.merge(pay_total, on="order_id", how="left")
fp["pago_key"] = fp.apply(
    lambda r: pago_key_map.get((r["payment_type"], r["rango_cuotas"]), 0)
    if pd.notna(r.get("payment_type")) else 0,
    axis=1,
).astype(int)

# num_items
num_items = items.groupby("order_id").size().reset_index(name="num_items")
fp = fp.merge(num_items, on="order_id", how="left")
fp["num_items"] = fp["num_items"].fillna(0).astype(int)

fp["cantidad_pedidos"] = 1

fact_pedidos = fp[[
    "order_id",
    "fecha_compra_key", "fecha_entrega_key", "fecha_estimada_key",
    "cliente_key", "estado_key", "pago_key",
    "dias_entrega", "dias_retraso", "entrega_a_tiempo",
    "review_score", "payment_value_total", "num_items", "cantidad_pedidos",
]].copy()

# Tipos
fact_pedidos["dias_entrega"] = fact_pedidos["dias_entrega"].astype("Int64")
fact_pedidos["dias_retraso"] = fact_pedidos["dias_retraso"].astype("Int64")
fact_pedidos["payment_value_total"] = fact_pedidos["payment_value_total"].round(2)

log(f"  fact_pedidos: {len(fact_pedidos):,} filas")

# ---------------------------------------------------------------------------
# 11. fact_ventas_items
# ---------------------------------------------------------------------------
log("11. Construyendo fact_ventas_items...")
fi = items.copy()
fi = fi.merge(orders[["order_id", "customer_id", "order_status", "order_purchase_timestamp"]], on="order_id", how="left")
fi = fi.merge(cust_map, on="customer_id", how="left")

fi["fecha_compra_key"] = fi["order_purchase_timestamp"].apply(to_fecha_key)
fi["cliente_key"] = fi["customer_unique_id"].map(cust_key_map).fillna(0).astype(int)
fi["producto_key"] = fi["product_id"].map(prod_key_map).fillna(0).astype(int)
fi["vendedor_key"] = fi["seller_id"].map(vend_key_map).fillna(0).astype(int)
fi["estado_key"] = fi["order_status"].map(estado_key_map).fillna(0).astype(int)

fi["total_item"] = (fi["price"] + fi["freight_value"]).round(2)
fi["cantidad"] = 1

fact_ventas_items = fi[[
    "order_id", "order_item_id",
    "fecha_compra_key", "cliente_key", "producto_key", "vendedor_key", "estado_key",
    "price", "freight_value", "total_item", "cantidad",
]].copy()

fact_ventas_items["price"] = fact_ventas_items["price"].round(2)
fact_ventas_items["freight_value"] = fact_ventas_items["freight_value"].round(2)

log(f"  fact_ventas_items: {len(fact_ventas_items):,} filas")

# ---------------------------------------------------------------------------
# 12. Guardar CSV
# ---------------------------------------------------------------------------
log("12. Guardando archivos CSV en clean/...")

def save_csv(df, name):
    path = CLEAN / name
    df.to_csv(path, index=False, na_rep="")
    log(f"  {name}: {len(df):,} filas, {len(df.columns)} columnas")

save_csv(dim_fecha, "dim_fecha.csv")
save_csv(dim_cliente, "dim_cliente.csv")
save_csv(dim_producto, "dim_producto.csv")
save_csv(dim_vendedor, "dim_vendedor.csv")
save_csv(dim_estado, "dim_estado_pedido.csv")
save_csv(dim_pago, "dim_pago.csv")
save_csv(fact_pedidos, "fact_pedidos.csv")
save_csv(fact_ventas_items, "fact_ventas_items.csv")

# ---------------------------------------------------------------------------
# 13. Validaciones rápidas
# ---------------------------------------------------------------------------
log("13. Validaciones de integridad...")
assert fact_pedidos["order_id"].is_unique
assert fact_ventas_items.duplicated(subset=["order_id", "order_item_id"]).sum() == 0
assert set(fact_ventas_items["order_id"]) - set(fact_pedidos["order_id"]) == set()
log("  PK únicas y FK de order_id OK")

ingresos = fact_ventas_items["price"].sum()
log(f"  Ingresos totales (suma price): {ingresos:,.2f}")

# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
log(f"Log guardado en {LOG_FILE}")
log("ETL completado correctamente.")
