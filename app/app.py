"""
Dashboard Olist - Business Intelligence
Entregable 3 · Streamlit + PostgreSQL
Universidad Estatal Península de Santa Elena
Estudiante: TOMALA GONZALEZ JUSTIN ARIEL
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from db import call_fn, get_categorias, get_estados, run_query

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Olist · BI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos
st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .kpi-value { font-size: 1.8rem; font-weight: 700; margin: 0.3rem 0; }
    .kpi-label { font-size: 0.85rem; opacity: 0.9; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar - Filtros globales
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Filtros")
st.sidebar.markdown("---")

# Fechas por defecto: todo el rango
fecha_ini = st.sidebar.date_input(
    "Fecha inicio",
    value=date(2017, 1, 1),
    min_value=date(2016, 9, 1),
    max_value=date(2018, 10, 31),
    key="fecha_ini",
)
fecha_fin = st.sidebar.date_input(
    "Fecha fin",
    value=date(2018, 8, 31),
    min_value=date(2016, 9, 1),
    max_value=date(2018, 10, 31),
    key="fecha_fin",
)

# Categorías y estados (con caché)
@st.cache_data(ttl=600)
def load_filtros():
    cats = get_categorias()
    ests = get_estados()
    return cats, ests

try:
    categorias, estados = load_filtros()
except Exception as e:
    st.error(f"No se pudo conectar a PostgreSQL: {e}")
    st.info("Verifica que el contenedor esté en ejecución: `docker compose up -d`")
    st.stop()

categoria_sel = st.sidebar.selectbox(
    "Categoría de producto",
    options=["Todas"] + categorias,
    index=0,
)
estado_sel = st.sidebar.selectbox(
    "Estado del cliente",
    options=["Todos"] + estados,
    index=0,
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Restablecer filtros"):
    st.rerun()

st.sidebar.markdown("""
**Dataset:** Brazilian E-Commerce (Olist)  
**Fuente:** PostgreSQL · esquema `dw`  
**Período datos:** Sep 2016 – Oct 2018
""")

# Parámetros para las funciones SQL
p_ini = fecha_ini.isoformat() if fecha_ini else None
p_fin = fecha_fin.isoformat() if fecha_fin else None
p_cat = None if categoria_sel == "Todas" else categoria_sel
p_est = None if estado_sel == "Todos" else estado_sel


def params_ventas():
    return {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_categoria": p_cat, "p_estado_cliente": p_est}


def params_logistica():
    return {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_estado_cliente": p_est}


def params_vendedores():
    return {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_categoria": p_cat}


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📊 Dashboard Olist · Business Intelligence")
st.caption("Marketplace brasileño · Análisis comercial, logístico y de satisfacción")

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["💰 Ventas", "🚚 Logística y Satisfacción", "🏪 Vendedores"])

# ===========================================================================
# VISTA 1: VENTAS
# ===========================================================================
with tab1:
    st.subheader("Evolución de ventas y categorías con más ingresos")

    # KPI
    try:
        kpi = call_fn("fn_kpi_ventas", params_ventas())
        ingresos = float(kpi["ingresos"].iloc[0])
        pedidos = int(kpi["pedidos"].iloc[0])
        ticket = float(kpi["ticket_promedio"].iloc[0])
        flete = float(kpi["flete"].iloc[0])
    except Exception as e:
        st.error(f"Error al consultar KPI de ventas: {e}")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Ingresos totales (GMV)", f"R$ {ingresos:,.0f}")
    with c2:
        st.metric("Pedidos", f"{pedidos:,}")
    with c3:
        st.metric("Ticket promedio", f"R$ {ticket:,.2f}")
    with c4:
        st.metric("Flete total", f"R$ {flete:,.0f}")

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)

    # Gráfico: ventas por mes
    with col_g1:
        st.markdown("**Ingresos por mes**")
        df_mes = call_fn("fn_ventas_por_mes", params_ventas())
        if not df_mes.empty:
            fig = px.line(
                df_mes, x="periodo", y="ingresos",
                markers=True,
                labels={"periodo": "Período", "ingresos": "Ingresos (R$)"},
            )
            fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
            fig.update_traces(line_color="#2d5a87", line_width=2.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos para el período seleccionado.")

    # Gráfico: top categorías
    with col_g2:
        st.markdown("**Top 8 categorías por ingresos**")
        params_cat = {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_estado_cliente": p_est, "p_limite": 8}
        df_cat = call_fn("fn_top_categorias", params_cat)
        if not df_cat.empty:
            fig = px.bar(
                df_cat, x="ingresos", y="categoria", orientation="h",
                text="pct_total",
                labels={"ingresos": "Ingresos (R$)", "categoria": "Categoría"},
                color="ingresos", color_continuous_scale="Blues",
            )
            fig.update_layout(
                height=350, margin=dict(t=20, b=20),
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
            )
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos.")

    # Tabla de detalle
    st.markdown("**Detalle de pedidos recientes**")
    params_det = {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_estado_cliente": p_est, "p_limite": 50}
    df_det = call_fn("fn_detalle_pedidos", params_det)
    if not df_det.empty:
        st.dataframe(
            df_det.rename(columns={
                "order_id": "Pedido",
                "fecha_compra": "Fecha",
                "estado_cliente": "Estado",
                "order_status": "Status",
                "dias_entrega": "Días entrega",
                "entrega_a_tiempo": "A tiempo",
                "review_score": "Puntaje",
                "payment_value_total": "Pago total",
                "num_items": "Ítems",
            }),
            use_container_width=True,
            height=300,
        )
    else:
        st.info("Sin pedidos para los filtros seleccionados.")

# ===========================================================================
# VISTA 2: LOGÍSTICA Y SATISFACCIÓN
# ===========================================================================
with tab2:
    st.subheader("Eficiencia logística y satisfacción del cliente")
    st.caption("Nota: el filtro de categoría no aplica aquí (un pedido puede tener varias categorías).")

    try:
        kpi_log = call_fn("fn_kpi_logistica", params_logistica())
        kpi_sat = call_fn("fn_kpi_satisfaccion", params_logistica())
        entregados = int(kpi_log["pedidos_entregados"].iloc[0])
        pct_tiempo = float(kpi_log["pct_a_tiempo"].iloc[0]) if pd.notna(kpi_log["pct_a_tiempo"].iloc[0]) else 0
        dias_prom = float(kpi_log["dias_promedio"].iloc[0]) if pd.notna(kpi_log["dias_promedio"].iloc[0]) else 0
        puntaje = float(kpi_sat["puntaje_promedio"].iloc[0]) if pd.notna(kpi_sat["puntaje_promedio"].iloc[0]) else 0
        pct_neg = float(kpi_sat["pct_negativas"].iloc[0]) if pd.notna(kpi_sat["pct_negativas"].iloc[0]) else 0
    except Exception as e:
        st.error(f"Error al consultar logística/satisfacción: {e}")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pedidos entregados", f"{entregados:,}")
    with c2:
        st.metric("% Entrega a tiempo", f"{pct_tiempo:.1f}%")
    with c3:
        st.metric("Días promedio de entrega", f"{dias_prom:.1f}")
    with c4:
        st.metric("Puntaje promedio", f"{puntaje:.2f} / 5")

    st.markdown("---")

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.markdown("**% Entrega a tiempo por estado del cliente**")
        df_est = call_fn("fn_entrega_por_estado", {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin})
        if not df_est.empty:
            fig = px.bar(
                df_est.head(15), x="estado", y="pct_a_tiempo",
                color="pct_a_tiempo", color_continuous_scale="RdYlGn",
                labels={"estado": "Estado", "pct_a_tiempo": "% a tiempo"},
                text="pct_a_tiempo",
            )
            fig.update_layout(height=350, margin=dict(t=20, b=20), coloraxis_showscale=False)
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos suficientes.")

    with col_g4:
        st.markdown("**Puntaje promedio según puntualidad de entrega**")
        df_sat = call_fn("fn_satisfaccion_vs_entrega", params_logistica())
        if not df_sat.empty:
            fig = px.bar(
                df_sat, x="tipo_entrega", y="puntaje_promedio",
                color="tipo_entrega",
                color_discrete_map={"A tiempo": "#2ecc71", "Tardía": "#e74c3c", "Sin dato": "#95a5a6"},
                text="puntaje_promedio",
                labels={"tipo_entrega": "Tipo de entrega", "puntaje_promedio": "Puntaje promedio"},
            )
            fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
            fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
            # Insight
            if len(df_sat) >= 2:
                a_tiempo = df_sat[df_sat["tipo_entrega"] == "A tiempo"]["puntaje_promedio"]
                tardia = df_sat[df_sat["tipo_entrega"] == "Tardía"]["puntaje_promedio"]
                if not a_tiempo.empty and not tardia.empty:
                    st.info(
                        f"💡 Los pedidos entregados a tiempo tienen un puntaje de **{a_tiempo.iloc[0]:.2f}**, "
                        f"frente a **{tardia.iloc[0]:.2f}** en entregas tardías. "
                        f"La puntualidad impacta fuertemente la satisfacción."
                    )
        else:
            st.info("Sin datos.")

    st.markdown(f"**% de reseñas negativas (1-2 estrellas):** {pct_neg:.1f}%")

    # Tabla
    st.markdown("**Detalle de pedidos entregados**")
    params_det2 = {"p_fecha_ini": p_ini, "p_fecha_fin": p_fin, "p_estado_cliente": p_est, "p_limite": 50}
    df_det2 = call_fn("fn_detalle_pedidos", params_det2)
    if not df_det2.empty:
        # Solo entregados
        df_det2 = df_det2[df_det2["order_status"] == "delivered"] if "order_status" in df_det2.columns else df_det2
        st.dataframe(df_det2, use_container_width=True, height=280)

# ===========================================================================
# VISTA 3: VENDEDORES
# ===========================================================================
with tab3:
    st.subheader("Concentración de ventas por vendedor")
    st.caption("Nota: el filtro de estado del cliente no aplica en esta vista.")

    try:
        conc = call_fn("fn_concentracion_vendedores", params_vendedores())
        vend_activos = int(conc["vendedores_activos"].iloc[0])
        pct_top10 = float(conc["pct_ingresos_top10"].iloc[0]) if pd.notna(conc["pct_ingresos_top10"].iloc[0]) else 0
        lider = float(conc["ingresos_lider"].iloc[0]) if pd.notna(conc["ingresos_lider"].iloc[0]) else 0
    except Exception as e:
        st.error(f"Error al consultar vendedores: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Vendedores activos", f"{vend_activos:,}")
    with c2:
        st.metric("% ingresos del 10% superior", f"{pct_top10:.1f}%")
    with c3:
        st.metric("Ingresos del mayor vendedor", f"R$ {lider:,.0f}")

    st.markdown("---")

    col_g5, col_g6 = st.columns(2)

    with col_g5:
        st.markdown("**Top 10 vendedores por ingresos**")
        params_top = {**params_vendedores(), "p_limite": 10}
        df_vend = call_fn("fn_top_vendedores", params_top)
        if not df_vend.empty:
            # Acortar seller_id para visualización
            df_vend["seller_short"] = df_vend["seller_id"].str[:8] + "…"
            fig = px.bar(
                df_vend, x="ingresos", y="seller_short", orientation="h",
                text="pct_total",
                labels={"ingresos": "Ingresos (R$)", "seller_short": "Vendedor"},
                color="ingresos", color_continuous_scale="Purples",
            )
            fig.update_layout(
                height=400, margin=dict(t=20, b=20),
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
            )
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos.")

    with col_g6:
        st.markdown("**Concentración de ingresos**")
        resto = max(0, 100 - pct_top10)
        fig = go.Figure(data=[go.Pie(
            labels=["Top 10% vendedores", "Resto de vendedores"],
            values=[pct_top10, resto],
            hole=0.45,
            marker_colors=["#6c5ce7", "#dfe6e9"],
            textinfo="label+percent",
        )])
        fig.update_layout(height=400, margin=dict(t=20, b=20), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        st.warning(
            f"⚠️ El **10% superior de vendedores concentra el {pct_top10:.1f}%** de los ingresos. "
            "El negocio depende significativamente de un grupo reducido de vendedores."
        )

    # Tabla ranking
    st.markdown("**Ranking de vendedores**")
    if not df_vend.empty:
        st.dataframe(
            df_vend[["seller_id", "ingresos", "pedidos", "pct_total"]].rename(columns={
                "seller_id": "Vendedor",
                "ingresos": "Ingresos (R$)",
                "pedidos": "Pedidos",
                "pct_total": "% del total",
            }),
            use_container_width=True,
            height=300,
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Universidad Estatal Península de Santa Elena · Carrera de Software · "
    "Inteligencia de Negocios · Entregable 3 · TOMALA GONZALEZ JUSTIN ARIEL · 2026-2"
)
