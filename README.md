# MI PRIMER DASHBOARD · Entregable 3

**Universidad Estatal Península de Santa Elena**  
**Carrera:** Software · **Asignatura:** Inteligencia de Negocios  
**Estudiante:** TOMALA GONZALEZ JUSTIN ARIEL · **Curso:** 6/1  
**Docente:** Ing. Anthony Pachay · **Período:** 2026-2

---

## Descripción

Solución de Business Intelligence de extremo a extremo sobre el dataset **Brazilian E-Commerce Public Dataset by Olist** (Kaggle).

```
Dataset Kaggle → Python/Pandas (ETL) → PostgreSQL (Data Mart dimensional)
→ Vistas/Funciones SQL → Streamlit → Dashboard interactivo → Decisiones
```

---

## Estructura del proyecto

```
olist_project/
├── raw_data/                 # CSV originales de Kaggle
├── clean/                    # CSV del Data Mart (salida del ETL)
├── sql/
│   ├── 01_crear_esquema.sql  # Dimensiones, hechos, índices
│   ├── 02_cargar_datos.sql   # COPY de CSV a PostgreSQL
│   ├── 03_validaciones.sql   # Verificaciones de integridad
│   └── 04_vistas_funciones.sql
├── scripts/
│   ├── etl_limpieza.py       # Limpieza y transformación
│   └── transformaciones_log.txt
├── app/
│   ├── app.py                # Aplicación Streamlit
│   └── db.py                 # Conexión a PostgreSQL
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Requisitos

- Docker y Docker Compose (recomendado) **o** PostgreSQL 14+
- Python 3.10+
- pip

---

## Instalación y ejecución

### 1. Clonar / descomprimir el proyecto

```bash
cd olist_project
```

### 2. Ejecutar el ETL (genera los CSV limpios)

```bash
python3 scripts/etl_limpieza.py
```

### 3. Levantar PostgreSQL

**Con Docker (recomendado):**

```bash
docker compose up -d
```

Luego cargar datos:

```bash
docker exec -i bi-postgres psql -U bi_user -d bi_database < sql/01_crear_esquema.sql
docker exec -i bi-postgres psql -U bi_user -d bi_database < sql/02_cargar_datos.sql
docker exec -i bi-postgres psql -U bi_user -d bi_database < sql/04_vistas_funciones.sql
```

**Sin Docker (PostgreSQL local):**

```bash
# Crear usuario y base (una sola vez)
sudo -u postgres psql -c "CREATE USER bi_user WITH PASSWORD 'bi_password' SUPERUSER;"
sudo -u postgres psql -c "CREATE DATABASE bi_database OWNER bi_user;"

export PGPASSWORD=bi_password
psql -h localhost -U bi_user -d bi_database -f sql/01_crear_esquema.sql

# Cargar cada tabla (ajustar ruta si es necesario)
for f in dim_fecha dim_cliente dim_producto dim_vendedor dim_estado_pedido dim_pago fact_pedidos fact_ventas_items; do
  psql -h localhost -U bi_user -d bi_database \
    -c "\COPY dw.$f FROM '$(pwd)/clean/${f}.csv' WITH (FORMAT csv, HEADER true, NULL '')"
done

psql -h localhost -U bi_user -d bi_database -f sql/04_vistas_funciones.sql
```

### 4. Validar datos

```bash
export PGPASSWORD=bi_password
psql -h localhost -U bi_user -d bi_database -f sql/03_validaciones.sql
```

### 5. Ejecutar el dashboard Streamlit

```bash
pip install -r requirements.txt
cd app
streamlit run app.py
```

Abrir en el navegador: http://localhost:8501

**Parámetros de conexión** (variables de entorno opcionales):

| Variable   | Valor por defecto |
|-----------|-------------------|
| DB_HOST   | localhost         |
| DB_PORT   | 5432              |
| DB_NAME   | bi_database       |
| DB_USER   | bi_user           |
| DB_PASS   | bi_password       |

---

## Modelo dimensional

**Constelación de hechos** (2 tablas de hechos + 6 dimensiones):

| Tabla de hechos     | Granularidad                                      |
|---------------------|---------------------------------------------------|
| `fact_ventas_items` | Una fila = un ítem vendido dentro de un pedido    |
| `fact_pedidos`      | Una fila = un pedido realizado por un cliente     |

**Dimensiones:** `dim_fecha`, `dim_cliente`, `dim_producto`, `dim_vendedor`, `dim_estado_pedido`, `dim_pago`.

---

## Preguntas de negocio y KPI

| Pregunta | KPI principales |
|----------|-----------------|
| P1. Evolución de ventas y categorías | Ingresos (GMV), ticket promedio, top categorías |
| P2. Eficiencia logística | % entrega a tiempo, días promedio de entrega |
| P3. Satisfacción del cliente | Puntaje promedio, % reseñas 1-2 estrellas |
| P4. Concentración de vendedores | % ingresos del top 10% de vendedores |

---

## Dashboard Streamlit

- **3 vistas:** Ventas · Logística y Satisfacción · Vendedores  
- **Filtros:** período, categoría de producto, estado del cliente  
- **KPI, gráficos (Plotly) y tablas** alimentados exclusivamente desde PostgreSQL (funciones SQL del esquema `dw`)  
- **Restricción cumplida:** no se leen CSV para los indicadores finales  

---

## Dataset

- **Nombre:** Brazilian E-Commerce Public Dataset by Olist  
- **Enlace:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce  
- **Período:** 4 sep 2016 – 17 oct 2018  
- **Registros:** 99.441 pedidos · 112.650 ítems  

---

## Autor

TOMALA GONZALEZ JUSTIN ARIEL  
Universidad Estatal Península de Santa Elena · 2026-2
