"""
Conexión a PostgreSQL - Data Mart Olist (esquema dw)
"""
import os
from sqlalchemy import create_engine, text
import pandas as pd

# Parámetros de conexión (pueden sobreescribirse con variables de entorno)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "bi_database")
DB_USER = os.getenv("DB_USER", "bi_user")
DB_PASS = os.getenv("DB_PASS", "bi_password")

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = (
            f"postgresql+psycopg2://{DB_USER}:{DB_PASS}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"client_encoding": "utf8"},
        )
    return _engine


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Ejecuta una consulta SQL y devuelve un DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def call_fn(fn_name: str, params: dict | None = None) -> pd.DataFrame:
    """
    Llama a una función SQL del esquema dw.
    params: dict con nombres de parámetros de la función.
    Ejemplo: call_fn('fn_kpi_ventas', {'p_fecha_ini': '2017-01-01', 'p_categoria': 'health_beauty'})
    """
    params = params or {}
    # Construir llamada con parámetros nombrados
    if params:
        placeholders = ", ".join(f"{k} => :{k}" for k in params)
        sql = f"SELECT * FROM dw.{fn_name}({placeholders})"
    else:
        sql = f"SELECT * FROM dw.{fn_name}()"
    return run_query(sql, params)


def get_categorias() -> list[str]:
    df = run_query("SELECT categoria FROM dw.vw_filtro_categorias")
    return df["categoria"].tolist()


def get_estados() -> list[str]:
    df = run_query("SELECT estado FROM dw.vw_filtro_estados_cliente")
    return df["estado"].tolist()
