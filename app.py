import base64
from dataclasses import replace
import importlib
from pathlib import Path
import unicodedata

import pandas as pd
import streamlit as st

from src.adapters.excel_reader import (
    get_excel_files,
    get_sheet_names,
    read_excel_sheet,
)
from src.core.column_detector import detect_key_columns, normalize_columns
from src.core.client_analysis import build_client_analysis
from src.core.client_trends import build_client_trend_analysis
from src.core.commercial_agenda import build_commercial_agenda
from src.core import commercial_time as commercial_time_module
from src.core.concentration_risk import build_concentration_risk
from src.core.data_quality import (
    build_analysis_datasets,
    build_document_quality_metrics,
    build_empty_sku_examples,
    build_missing_profitability_examples,
    build_possible_exact_duplicate_examples,
    build_profitability_coverage_metrics,
    build_quality_warnings,
    build_sku_coverage_metrics,
)
from src.core.level_classifier import classify_analysis_level
from src import commercial_excel as commercial_excel_module
from src import commercial_pdf as commercial_pdf_module


PROJECT_ROOT = Path(__file__).parent
LOGO_PATH = PROJECT_ROOT / "assets" / "logo-kappo.png"


st.set_page_config(
    page_title="Kappo | Diagnostico ejecutivo",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_kappo_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --kappo-navy: #082d5f;
            --kappo-blue: #0f5597;
            --kappo-cyan: #159bd7;
            --kappo-ink: #14233a;
            --kappo-muted: #5c6b7d;
            --kappo-line: #d8e2ec;
            --kappo-soft: #eef5fb;
        }

        .stApp {
            background: #f4f8fc;
            color: var(--kappo-ink);
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1480px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: var(--kappo-navy);
            border-right: 1px solid #0d467f;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.4rem;
        }

        [data-testid="stSidebar"] .sidebar-title {
            margin-bottom: 0.25rem;
            color: #ffffff;
            font-size: 1.35rem;
            font-weight: 700;
        }

        [data-testid="stSidebar"] .sidebar-copy {
            margin-bottom: 1.4rem;
            color: #bcd2e8;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #ffffff !important;
            font-weight: 600;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            border-color: #8eabc8;
            background: #f8fbfe;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.16) !important;
        }

        [data-testid="stSidebar"] [data-testid="stAlert"] {
            margin-top: 1rem;
            background: #e7f2fb;
            color: #15395f;
        }

        .kappo-header {
            display: grid;
            grid-template-columns: minmax(210px, 300px) 1fr;
            min-height: 172px;
            margin-bottom: 1.25rem;
            overflow: hidden;
            border: 1px solid #cddbe9;
            border-radius: 8px;
            background: #ffffff;
            box-shadow: 0 8px 24px rgba(8, 45, 95, 0.08);
        }

        .kappo-brand {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.75rem;
            background: #ffffff;
        }

        .kappo-brand img {
            width: 100%;
            max-width: 270px;
            height: auto;
        }

        .kappo-heading {
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 2rem 2.25rem;
            border-left: 7px solid var(--kappo-cyan);
            background: var(--kappo-navy);
            color: #ffffff;
        }

        .kappo-heading h1 {
            margin: 0 0 0.55rem;
            color: #ffffff;
            font-size: 2.35rem;
            line-height: 1.12;
            letter-spacing: 0;
        }

        .kappo-heading p {
            max-width: 900px;
            margin: 0;
            color: #dceafb;
            font-size: 1rem;
            line-height: 1.55;
        }

        h2, h3 {
            color: var(--kappo-navy) !important;
            letter-spacing: 0 !important;
        }

        h3 {
            margin-top: 1.8rem !important;
            padding-bottom: 0.55rem;
            border-bottom: 2px solid #d7e5f2;
        }

        [data-testid="stMetric"] {
            min-height: 108px;
            padding: 1rem 1.05rem;
            border: 1px solid var(--kappo-line);
            border-top: 4px solid var(--kappo-blue);
            border-radius: 7px;
            background: #ffffff;
            box-shadow: 0 4px 14px rgba(8, 45, 95, 0.06);
        }

        [data-testid="stMetricLabel"] {
            color: var(--kappo-muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--kappo-navy);
            font-weight: 700;
        }

        [data-testid="stAlert"] {
            border-radius: 6px;
            border-width: 1px;
            box-shadow: none;
        }

        [data-testid="stNotificationContentInfo"] {
            background: #eaf4fc;
            color: #173b63;
        }

        [data-testid="stNotificationContentWarning"] {
            background: #fff8e8;
            color: #624b16;
        }

        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--kappo-line);
            border-radius: 6px;
            background: #ffffff;
        }

        [data-testid="stExpander"] {
            border: 1px solid var(--kappo-line);
            border-radius: 6px;
            background: #ffffff;
        }

        [data-testid="stExpander"] summary {
            color: var(--kappo-navy);
            font-weight: 600;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.3rem;
            border-bottom: 1px solid var(--kappo-line);
        }

        .stTabs [data-baseweb="tab"] {
            min-height: 44px;
            padding: 0.55rem 0.85rem;
            color: #496176;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            color: var(--kappo-blue) !important;
        }

        .stSelectbox [data-baseweb="select"] > div,
        .stTextInput input,
        [data-testid="stFileUploaderDropzone"] {
            border-color: #c9d8e7;
            border-radius: 6px;
            background: #ffffff;
        }

        .stTextInput input:focus {
            border-color: var(--kappo-cyan);
            box-shadow: 0 0 0 1px var(--kappo-cyan);
        }

        .stDownloadButton button {
            min-height: 42px;
            border: 1px solid var(--kappo-blue);
            border-radius: 6px;
            background: var(--kappo-blue);
            color: #ffffff;
            font-weight: 700;
        }

        .stDownloadButton button:hover {
            border-color: var(--kappo-cyan);
            background: #0b477f;
            color: #ffffff;
        }

        hr {
            border-color: #d8e4ef !important;
        }

        @media (max-width: 760px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding-top: 0.8rem;
            }

            .kappo-header {
                grid-template-columns: 1fr;
            }

            .kappo-brand {
                padding: 1.1rem 1.5rem;
            }

            .kappo-brand img {
                max-width: 230px;
            }

            .kappo-heading {
                padding: 1.5rem;
                border-top: 5px solid var(--kappo-cyan);
                border-left: 0;
            }

            .kappo-heading h1 {
                font-size: 1.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kappo_header() -> None:
    logo_base64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <div class="kappo-header">
            <div class="kappo-brand">
                <img src="data:image/png;base64,{logo_base64}" alt="Kappo">
            </div>
            <div class="kappo-heading">
                <h1>Diagnostico ejecutivo de ventas</h1>
                <p>Kappo analiza el maximo nivel ejecutivo posible segun la
                calidad real del informe de ventas disponible.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_kappo_style()
render_kappo_header()

build_commercial_time_intelligence = importlib.reload(
    commercial_time_module
).build_commercial_time_intelligence
build_commercial_management_excel = importlib.reload(
    commercial_excel_module
).build_commercial_management_excel
build_executive_clients_pdf = importlib.reload(
    commercial_pdf_module
).build_executive_clients_pdf


def load_workbook_source():
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Carga de datos</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-copy">Seleccione el informe de ventas que desea analizar.</div>',
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "Cargar Excel de ventas",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
        )

        sample_files = get_excel_files(PROJECT_ROOT)
        selected_sample = None

        if sample_files:
            st.divider()
            selected_sample = st.selectbox(
                "Archivo disponible",
                options=[None, *sample_files],
                format_func=lambda value: (
                    "Seleccionar archivo..." if value is None else value.name
                ),
            )

    return uploaded_file or selected_sample


def format_number(value: int | float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def format_money(value: int | float) -> str:
    return "$" + f"{value:,.0f}".replace(",", ".")


def format_percentage(value: float) -> str:
    decimals = 2 if 0 < abs(value) < 0.001 else 1
    return f"{value:.{decimals}%}".replace(".", ",")


def format_date(value: pd.Timestamp) -> str:
    return value.strftime("%d/%m/%Y")


def format_optional_date(value: object) -> str:
    return "No determinada" if pd.isna(value) else format_date(pd.Timestamp(value))


def normalize_search_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    return "".join(
        character for character in text if not unicodedata.combining(character)
    ).casefold()


def format_alerts_table(data: pd.DataFrame) -> pd.DataFrame:
    table = data[
        [
            "cliente",
            "venta_total",
            "participacion",
            "venta_ultimos_3_meses",
            "venta_3_meses_anteriores",
            "variacion_absoluta",
            "variacion_porcentual",
            "ultimo_mes_con_compra",
            "tendencia",
            "alerta_comercial",
            "recomendacion_sugerida",
        ]
    ].copy()
    for column in [
        "venta_total",
        "venta_ultimos_3_meses",
        "venta_3_meses_anteriores",
        "variacion_absoluta",
    ]:
        table[column] = table[column].map(format_money)
    table["participacion"] = table["participacion"].map(format_percentage)
    table["variacion_porcentual"] = table["variacion_porcentual"].map(
        lambda value: "N/D" if pd.isna(value) else format_percentage(value)
    )
    table.columns = [
        "Cliente",
        "Venta total",
        "Participacion %",
        "Venta ultimos 3 meses",
        "Venta 3 meses anteriores",
        "Variacion absoluta",
        "Variacion %",
        "Ultimo mes con compra",
        "Tendencia",
        "Alerta comercial",
        "Recomendacion sugerida",
    ]
    return table


def show_alerts_table(data: pd.DataFrame, empty_message: str) -> None:
    if data.empty:
        st.info(empty_message)
    else:
        st.dataframe(
            format_alerts_table(data),
            use_container_width=True,
            hide_index=True,
        )


def format_agenda_table(data: pd.DataFrame) -> pd.DataFrame:
    data = ensure_agenda_semantic_columns(data)
    table = data[
        [
            "cliente",
            "vendedor_responsable_sugerido",
            "proxima_compra_esperada",
            "dias_atraso",
            "confianza_recompra",
            "venta_total",
            "participacion",
            "tendencia",
            "alerta_comercial",
            "prioridad_gestion",
            "tipo_sugerencia",
            "validacion_requerida_crm",
            "motivo_comercial",
        ]
    ].copy()
    table["venta_total"] = table["venta_total"].map(format_money)
    table["participacion"] = table["participacion"].map(format_percentage)
    table["proxima_compra_esperada"] = table["proxima_compra_esperada"].map(
        format_optional_date
    )
    table["dias_atraso"] = table["dias_atraso"].map(
        lambda value: "N/D" if pd.isna(value) else format_number(value)
    )
    table["confianza_recompra"] = table["confianza_recompra"].replace(
        {"Insuficiente": "Insuficiente historial"}
    )
    table.columns = [
        "Cliente",
        "Vendedor responsable sugerido",
        "Proxima compra esperada",
        "Dias de atraso",
        "Confianza recompra",
        "Venta total",
        "Participacion %",
        "Tendencia",
        "Alerta comercial",
        "Prioridad sugerida",
        "Tipo de sugerencia",
        "Validacion requerida en CRM",
        "Motivo comercial",
    ]
    return table


def show_agenda_table(data: pd.DataFrame, empty_message: str) -> None:
    if data.empty:
        st.info(empty_message)
    else:
        st.dataframe(
            format_agenda_table(data),
            use_container_width=True,
            hide_index=True,
        )


def ensure_agenda_semantic_columns(data: pd.DataFrame) -> pd.DataFrame:
    compatible_data = data.copy()
    if "vendedor_responsable_sugerido" not in compatible_data.columns:
        compatible_data["vendedor_responsable_sugerido"] = (
            "Sin vendedor identificado"
        )
    if "proxima_compra_esperada" not in compatible_data.columns:
        compatible_data["proxima_compra_esperada"] = pd.NaT
    if "dias_atraso" not in compatible_data.columns:
        compatible_data["dias_atraso"] = pd.NA
    if "confianza_recompra" not in compatible_data.columns:
        compatible_data["confianza_recompra"] = "Insuficiente"
    if "lectura_comercial_patron" not in compatible_data.columns:
        compatible_data["lectura_comercial_patron"] = "Historial insuficiente"
    if "sugerencia_por_tiempo" not in compatible_data.columns:
        compatible_data["sugerencia_por_tiempo"] = (
            "No inferir recompra; evaluar por venta o criterio comercial."
        )
    if "tipo_sugerencia" not in compatible_data.columns:
        compatible_data["tipo_sugerencia"] = compatible_data.get(
            "accion_sugerida", "Mantener seguimiento"
        )
    if "validacion_requerida_crm" not in compatible_data.columns:
        compatible_data["validacion_requerida_crm"] = (
            "Revisar si existe gestion, llamada, cotizacion o tarea abierta en CRM."
        )
    if "motivo_comercial" not in compatible_data.columns:
        if "por_que_importa" in compatible_data.columns:
            compatible_data["motivo_comercial"] = compatible_data["por_que_importa"]
        elif "motivo_prioridad" in compatible_data.columns:
            compatible_data["motivo_comercial"] = compatible_data["motivo_prioridad"]
        else:
            compatible_data["motivo_comercial"] = "Motivo comercial no disponible."
    return compatible_data


def format_commercial_time_table(data: pd.DataFrame) -> pd.DataFrame:
    table = data[
        [
            "cliente",
            "vendedor_responsable_sugerido",
            "ultima_compra",
            "ultimo_mes_con_compra",
            "dias_desde_ultima_compra",
            "categoria_recompra",
            "lectura_comercial_patron",
            "sugerencia_por_tiempo",
            "proxima_compra_esperada",
            "dias_atraso",
            "intervalo_mensual_mediano_dias",
            "confianza_recompra",
        ]
    ].copy()
    table["ultima_compra"] = table["ultima_compra"].map(format_optional_date)
    table["proxima_compra_esperada"] = table["proxima_compra_esperada"].map(
        format_optional_date
    )
    table["dias_desde_ultima_compra"] = table["dias_desde_ultima_compra"].map(
        format_number
    )
    table["intervalo_mensual_mediano_dias"] = table[
        "intervalo_mensual_mediano_dias"
    ].map(
        lambda value: "N/D" if pd.isna(value) else f"{format_number(value)} dias"
    )
    table["dias_atraso"] = table["dias_atraso"].map(format_number)
    table["confianza_recompra"] = table["confianza_recompra"].replace(
        {"Insuficiente": "Insuficiente historial"}
    )
    table.columns = [
        "Cliente",
        "Vendedor responsable sugerido",
        "Ultima compra",
        "Ultimo mes con compra",
        "Dias desde ultima compra",
        "Categoria de recompra",
        "Lectura comercial del patron",
        "Sugerencia por tiempo",
        "Proxima compra esperada",
        "Dias de atraso",
        "Ciclo tipico entre meses con compra",
        "Confianza",
    ]
    return table


def ensure_commercial_time_columns(data: pd.DataFrame) -> pd.DataFrame:
    compatible_data = data.copy()
    if "intervalo_mensual_mediano_dias" not in compatible_data.columns:
        compatible_data["intervalo_mensual_mediano_dias"] = compatible_data.get(
            "intervalo_mediano_dias",
            pd.Series(pd.NA, index=compatible_data.index),
        )
    if "ultimo_mes_con_compra" not in compatible_data.columns:
        last_purchase = pd.to_datetime(
            compatible_data.get(
                "ultima_compra",
                pd.Series(pd.NaT, index=compatible_data.index),
            ),
            errors="coerce",
        )
        compatible_data["ultimo_mes_con_compra"] = last_purchase.dt.strftime(
            "%m/%Y"
        )
    if "categoria_recompra" not in compatible_data.columns:
        overdue = compatible_data.get(
            "recompra_atrasada",
            pd.Series(False, index=compatible_data.index),
        ).fillna(False)
        normal_cycle = compatible_data.get(
            "dentro_ciclo_normal",
            pd.Series(False, index=compatible_data.index),
        ).fillna(False)
        confidence = compatible_data.get(
            "confianza_recompra",
            pd.Series("Insuficiente", index=compatible_data.index),
        )
        compatible_data["categoria_recompra"] = "Patron irregular"
        compatible_data.loc[confidence.isin(["Alta", "Media"]), "categoria_recompra"] = (
            "Confianza alta/media"
        )
        compatible_data.loc[confidence.eq("Insuficiente"), "categoria_recompra"] = (
            "Historial insuficiente"
        )
        compatible_data.loc[normal_cycle.astype(bool), "categoria_recompra"] = (
            "Dentro de ciclo normal"
        )
        compatible_data.loc[overdue.astype(bool), "categoria_recompra"] = (
            "Recompra esperada atrasada"
        )
    if {
        "lectura_comercial_patron",
        "sugerencia_por_tiempo",
    }.issubset(compatible_data.columns):
        return compatible_data

    if compatible_data.empty:
        compatible_data["lectura_comercial_patron"] = pd.Series(dtype="string")
        compatible_data["sugerencia_por_tiempo"] = pd.Series(dtype="string")
        return compatible_data

    purchase_count_source = compatible_data.get(
        "cantidad_compras",
        pd.Series(0, index=compatible_data.index),
    )
    purchase_count = pd.to_numeric(purchase_count_source, errors="coerce").fillna(0)
    missing_dates = pd.Series(pd.NaT, index=compatible_data.index)
    first_purchase = pd.to_datetime(
        compatible_data.get("primera_compra", missing_dates), errors="coerce"
    )
    last_purchase = pd.to_datetime(
        compatible_data.get("ultima_compra", missing_dates), errors="coerce"
    )
    purchase_window = (last_purchase - first_purchase).dt.days
    concentrated = purchase_count.ge(2) & purchase_window.le(30)

    compatible_data["lectura_comercial_patron"] = compatible_data[
        "confianza_recompra"
    ].map(
        {
            "Alta": "Ciclo consistente",
            "Media": "Ciclo razonable",
            "Baja": "Patrón irregular",
            "Insuficiente": "Historial insuficiente",
        }
    )
    compatible_data.loc[concentrated, "lectura_comercial_patron"] = (
        "Compras concentradas"
    )

    def build_compatible_suggestion(row: pd.Series) -> str:
        pattern = row["lectura_comercial_patron"]
        if pattern == "Compras concentradas":
            return (
                "Revisar manualmente; compras concentradas no permiten inferir "
                "ciclo estable."
            )
        if pattern == "Patrón irregular":
            return "Monitorear; no priorizar sólo por ciclo."
        if pattern == "Historial insuficiente":
            return "No inferir recompra; evaluar por venta o criterio comercial."
        if pattern == "Ciclo consistente" and bool(row.get("recompra_atrasada")):
            return "Revisar recuperación comercial."
        if pattern == "Ciclo razonable" and bool(row.get("recompra_atrasada")):
            return "Validar si corresponde contacto comercial."
        return "Monitorear próxima recompra según patrón histórico."

    compatible_data["sugerencia_por_tiempo"] = compatible_data.apply(
        build_compatible_suggestion,
        axis=1,
    )
    return compatible_data


def add_suggested_seller(
    agenda: pd.DataFrame,
    sales_df: pd.DataFrame,
    detection,
) -> pd.DataFrame:
    enriched_agenda = agenda.copy()
    fallback = "Sin vendedor identificado"
    client_field = detection.get("cliente")
    date_field = detection.get("fecha")
    seller_field = detection.get("vendedor")
    client_column = client_field.detected_column if client_field else None
    date_column = date_field.detected_column if date_field else None
    seller_column = seller_field.detected_column if seller_field else None
    required_columns = {client_column, date_column, seller_column}

    if (
        enriched_agenda.empty
        or None in required_columns
        or not required_columns.issubset(sales_df.columns)
    ):
        enriched_agenda["vendedor_responsable_sugerido"] = fallback
        return enriched_agenda

    sales = sales_df[[client_column, date_column, seller_column]].copy()
    sales["_cliente"] = sales[client_column].astype("string").str.strip()
    sales["_fecha"] = pd.to_datetime(sales[date_column], errors="coerce", dayfirst=True)
    sales["_vendedor"] = sales[seller_column].astype("string").str.strip()
    sales.loc[
        sales["_vendedor"].isna() | sales["_vendedor"].eq(""), "_vendedor"
    ] = pd.NA
    sales = sales[
        sales["_cliente"].notna()
        & sales["_cliente"].ne("")
        & sales["_fecha"].notna()
    ]

    seller_by_client = {}
    if not sales.empty:
        latest_date = sales.groupby("_cliente")["_fecha"].transform("max")
        latest_sales = sales[sales["_fecha"].eq(latest_date)]
        seller_by_client = (
            latest_sales.dropna(subset=["_vendedor"])
            .drop_duplicates(subset=["_cliente"], keep="last")
            .set_index("_cliente")["_vendedor"]
            .astype(str)
            .to_dict()
        )

    enriched_agenda["vendedor_responsable_sugerido"] = (
        enriched_agenda["cliente"]
        .astype("string")
        .str.strip()
        .map(seller_by_client)
        .fillna(fallback)
    )
    return enriched_agenda


def render_dataframe_expander(title: str, data: pd.DataFrame, empty_message: str) -> None:
    with st.expander(title):
        if data.empty:
            st.write(empty_message)
        else:
            st.dataframe(data, use_container_width=True, hide_index=True)


def build_general_quality(level, sku_coverage, profitability_coverage) -> str:
    if (
        level.level == 4
        and profitability_coverage.profitability_coverage_level == "alta"
        and sku_coverage.empty_sku_sales_percentage < 0.15
        and profitability_coverage.without_valid_cost_sales_percentage < 0.05
    ):
        return "Alta"
    if level.level >= 2 and profitability_coverage.profitability_coverage_level != "baja":
        return "Media"
    return "Baja"


def build_profitability_status(level, profitability_coverage) -> str:
    if level.level < 4:
        return "No disponible"
    if profitability_coverage.profitability_coverage_level == "alta":
        return "Buena cobertura"
    if profitability_coverage.profitability_coverage_level == "parcial":
        return "Cobertura parcial"
    return "Cobertura baja"


def build_enabled_analyses(level, detection) -> list[str]:
    analyses = [
        "Ranking de clientes por venta.",
        "Concentracion y Pareto de clientes.",
        "Evolucion mensual por cliente.",
        "Clientes en crecimiento/caida.",
    ]

    if level.level >= 3:
        analyses.extend(
            [
                "Ventas por producto/SKU.",
                "Mix comercial.",
            ]
        )

    if level.level >= 4:
        analyses.extend(
            [
                "Rentabilidad por cliente.",
                "Rentabilidad por producto/SKU.",
            ]
        )

    if detection.has("vendedor"):
        analyses.append("Rentabilidad por vendedor.")

    if detection.has("categoria_familia"):
        analyses.append("Analisis por familia/categoria.")

    return analyses


def build_period_detail(df: pd.DataFrame, detection) -> dict[str, object]:
    date_field = detection.get("fecha")
    date_column = date_field.detected_column if date_field else None

    if not date_column or date_column not in df.columns:
        return {
            "date_column": None,
            "min_date": None,
            "max_date": None,
            "valid_date_rows": 0,
            "invalid_date_rows": len(df),
            "label": "Periodo no determinado",
        }

    parsed_dates = pd.to_datetime(df[date_column], errors="coerce", dayfirst=True)
    valid_dates = parsed_dates.dropna()
    valid_date_rows = int(parsed_dates.notna().sum())
    invalid_date_rows = int(parsed_dates.isna().sum())

    if valid_dates.empty:
        return {
            "date_column": date_column,
            "min_date": None,
            "max_date": None,
            "valid_date_rows": valid_date_rows,
            "invalid_date_rows": invalid_date_rows,
            "label": "Periodo no determinado",
        }

    min_date = valid_dates.min()
    max_date = valid_dates.max()

    return {
        "date_column": date_column,
        "min_date": min_date,
        "max_date": max_date,
        "valid_date_rows": valid_date_rows,
        "invalid_date_rows": invalid_date_rows,
        "label": f"{format_date(min_date)} al {format_date(max_date)}",
    }


workbook_source = load_workbook_source()

if workbook_source is None:
    st.sidebar.info("Esperando un archivo de ventas para iniciar el analisis.")
    st.stop()

try:
    sheet_names = get_sheet_names(workbook_source)
except Exception as exc:
    st.sidebar.error(f"No fue posible leer el archivo Excel: {exc}")
    st.stop()

selected_sheet = st.sidebar.selectbox("Hoja disponible", options=sheet_names)

try:
    df = read_excel_sheet(workbook_source, selected_sheet)
except Exception as exc:
    st.sidebar.error(f"No fue posible leer la hoja seleccionada: {exc}")
    st.stop()

if df.empty:
    st.sidebar.warning("La hoja seleccionada no contiene filas de datos.")
    st.stop()

st.sidebar.success(
    f"Datos listos: {format_number(len(df))} filas en la hoja {selected_sheet}."
)

normalized_df, normalization_map = normalize_columns(df)
detection = detect_key_columns(df.columns)
level = classify_analysis_level(detection)
warnings = build_quality_warnings(df, detection)
document_metrics = build_document_quality_metrics(df, detection)
duplicate_examples = build_possible_exact_duplicate_examples(df, detection)
sku_coverage = build_sku_coverage_metrics(df, detection)
profitability_coverage = build_profitability_coverage_metrics(df, detection)
analysis_datasets = build_analysis_datasets(df, detection)
client_analysis = build_client_analysis(analysis_datasets["dataset_cliente"], detection)
concentration_risk = build_concentration_risk(client_analysis)
client_trends = build_client_trend_analysis(
    analysis_datasets["dataset_cliente"], detection, client_analysis
)
commercial_time = build_commercial_time_intelligence(
    analysis_datasets["dataset_cliente"], detection
)
commercial_time = replace(
    commercial_time,
    clients=ensure_commercial_time_columns(commercial_time.clients),
)
try:
    commercial_agenda = build_commercial_agenda(
        client_trends.client_alerts,
        median_client_sales=client_analysis.median_sales_per_client,
        sales_df=analysis_datasets["dataset_cliente"],
        detection=detection,
    )
except TypeError as exc:
    if "unexpected keyword argument" not in str(exc):
        raise
    commercial_agenda = build_commercial_agenda(
        client_trends.client_alerts,
        median_client_sales=client_analysis.median_sales_per_client,
    )

enriched_agenda = add_suggested_seller(
    commercial_agenda.agenda,
    analysis_datasets["dataset_cliente"],
    detection,
)
time_guide_columns = [
    "cliente",
    "ultima_compra",
    "ultimo_mes_con_compra",
    "dias_desde_ultima_compra",
    "intervalo_mensual_mediano_dias",
    "proxima_compra_esperada",
    "dias_atraso",
    "categoria_recompra",
    "confianza_recompra",
    "lectura_comercial_patron",
    "sugerencia_por_tiempo",
]
if commercial_time.clients.empty:
    enriched_agenda["ultima_compra"] = pd.NaT
    enriched_agenda["dias_desde_ultima_compra"] = pd.NA
    enriched_agenda["proxima_compra_esperada"] = pd.NaT
    enriched_agenda["intervalo_mensual_mediano_dias"] = pd.NA
    enriched_agenda["dias_atraso"] = pd.NA
    enriched_agenda["categoria_recompra"] = "Historial insuficiente"
    enriched_agenda["confianza_recompra"] = "Insuficiente"
    enriched_agenda["lectura_comercial_patron"] = "Historial insuficiente"
    enriched_agenda["sugerencia_por_tiempo"] = (
        "No inferir recompra; evaluar por venta o criterio comercial."
    )
else:
    if "ultimo_mes_con_compra" in enriched_agenda.columns:
        enriched_agenda["ultimo_mes_con_compra_alertas"] = enriched_agenda[
            "ultimo_mes_con_compra"
        ]
    time_guide = commercial_time.clients[time_guide_columns].rename(
        columns={"ultimo_mes_con_compra": "ultimo_mes_con_compra_tiempo"}
    )
    enriched_agenda = enriched_agenda.merge(
        time_guide,
        on="cliente",
        how="left",
        validate="one_to_one",
    )
    if "ultimo_mes_con_compra" in enriched_agenda.columns:
        enriched_agenda["ultimo_mes_con_compra"] = enriched_agenda[
            "ultimo_mes_con_compra_tiempo"
        ].combine_first(enriched_agenda["ultimo_mes_con_compra"])
    else:
        enriched_agenda["ultimo_mes_con_compra"] = enriched_agenda[
            "ultimo_mes_con_compra_tiempo"
        ]
    enriched_agenda = enriched_agenda.drop(columns=["ultimo_mes_con_compra_tiempo"])
commercial_agenda = replace(commercial_agenda, agenda=enriched_agenda)
empty_sku_examples = build_empty_sku_examples(df, detection)
missing_profitability_examples = build_missing_profitability_examples(df, detection)
period_detail = build_period_detail(df, detection)

general_quality = build_general_quality(level, sku_coverage, profitability_coverage)
profitability_status = build_profitability_status(level, profitability_coverage)
enabled_analyses = build_enabled_analyses(level, detection)

st.info(f"Periodo analizado: {period_detail['label']}")

executive_kpis_1 = st.columns(4)
executive_kpis_1[0].metric("Nivel detectado", f"Nivel {level.level}")
executive_kpis_1[1].metric("Calidad general de data", general_quality)
executive_kpis_1[2].metric("Filas analizadas", format_number(len(df)))
executive_kpis_1[3].metric("Venta total", format_money(profitability_coverage.total_sales))

executive_kpis_2 = st.columns(4)
executive_kpis_2[0].metric(
    "Cobertura SKU",
    format_percentage(sku_coverage.valid_sku_sales_percentage),
)
executive_kpis_2[1].metric(
    "Cobertura costo/margen",
    profitability_coverage.profitability_coverage_level.title(),
)
executive_kpis_2[2].metric(
    "Margen comercial calculado",
    "N/D"
    if profitability_coverage.calculated_commercial_margin is None
    else format_percentage(profitability_coverage.calculated_commercial_margin),
)
executive_kpis_2[3].metric("Estado de rentabilidad", profitability_status)

if level.level == 4 and general_quality == "Alta":
    st.success(
        "El archivo permite analisis ejecutivo Nivel 4. La data tiene cobertura "
        "suficiente para analisis de ventas, clientes, productos/SKU y "
        "rentabilidad comercial. Las limitaciones detectadas son puntuales y no "
        "bloquean el analisis."
    )
elif level.level >= 2:
    st.warning(
        "El archivo permite analisis comercial, pero existen limitaciones de "
        "cobertura que deben considerarse antes de generar conclusiones ejecutivas."
    )
else:
    st.error(
        "El archivo no tiene cobertura suficiente para un analisis ejecutivo "
        "confiable sin correcciones previas."
    )

with st.expander("Alcance y limitaciones del analisis"):
    st.markdown("**Analisis habilitados**")
    analysis_cols = st.columns(2)
    for index, item in enumerate(enabled_analyses):
        analysis_cols[index % 2].write(f"- {item}")

    st.markdown("**Limitaciones resumidas**")
    st.write(
        f"- Documentos multilinea detectados: "
        f"{format_number(document_metrics.multiline_documents)} documentos, "
        "comportamiento esperable en ventas detalladas."
    )
    if document_metrics.possible_exact_duplicates > 0:
        st.write(
            f"- Posibles duplicados exactos: "
            f"{format_number(document_metrics.possible_exact_duplicates)} casos / "
            f"{format_number(document_metrics.possible_exact_duplicate_rows)} filas, "
            "revision menor."
        )
    else:
        st.write("- Posibles duplicados exactos: no detectados.")
    st.write(
        f"- SKU vacio: {format_percentage(sku_coverage.empty_sku_sales_percentage)} "
        "de la venta, impacto bajo."
    )
    st.write(
        f"- Venta sin costo valido: "
        f"{format_percentage(profitability_coverage.without_valid_cost_sales_percentage)}, "
        "impacto inmaterial."
    )
    if profitability_coverage.profitability_coverage_level == "alta":
        st.write("- Rentabilidad: buena cobertura.")
    elif profitability_coverage.profitability_coverage_level == "parcial":
        st.write("- Rentabilidad: cobertura parcial.")
    else:
        st.write("- Rentabilidad: cobertura baja.")

st.divider()
st.subheader("Analisis base de clientes")

client_kpis = st.columns(6)
client_kpis[0].metric("Clientes unicos", format_number(client_analysis.total_clients))
client_kpis[1].metric(
    "Clientes que explican 80%",
    format_number(client_analysis.clients_for_80_percent),
)
client_kpis[2].metric(
    "Concentracion Top 5",
    format_percentage(client_analysis.top_5_concentration),
)
client_kpis[3].metric(
    "Concentracion Top 10",
    format_percentage(client_analysis.top_10_concentration),
)
client_kpis[4].metric(
    "Venta promedio por cliente",
    format_money(client_analysis.average_sales_per_client),
)
client_kpis[5].metric(
    "Venta mediana por cliente",
    format_money(client_analysis.median_sales_per_client),
)

st.info(
    f"La venta presenta una concentracion relevante: los Top 10 clientes explican "
    f"{format_percentage(client_analysis.top_10_concentration)} de la venta total. "
    f"El 80% de la venta se concentra en "
    f"{format_number(client_analysis.clients_for_80_percent)} clientes, lo que "
    "permite identificar el nucleo comercial prioritario."
)

client_table = client_analysis.ranking.head(20).copy()
client_table["venta_total"] = client_table["venta_total"].map(format_money)
client_table["participacion"] = client_table["participacion"].map(format_percentage)
client_table["participacion_acumulada"] = client_table[
    "participacion_acumulada"
].map(format_percentage)
client_table.columns = [
    "Ranking",
    "Cliente",
    "Venta total",
    "Participacion %",
    "Participacion acumulada %",
    "Clasificacion cliente",
]
st.dataframe(client_table, use_container_width=True, hide_index=True)

top_10_chart = client_analysis.ranking.head(10).set_index("cliente")[["venta_total"]]
st.caption("Top 10 clientes por venta")
st.bar_chart(top_10_chart, horizontal=True, use_container_width=True)

st.subheader("Riesgo de concentracion comercial")

risk_kpis_1 = st.columns(5)
risk_kpis_1[0].metric("Riesgo de concentracion", concentration_risk.risk_level)
risk_kpis_1[1].metric(
    "Concentracion Top 1",
    format_percentage(concentration_risk.top_1_concentration),
)
risk_kpis_1[2].metric(
    "Concentracion Top 3",
    format_percentage(concentration_risk.top_3_concentration),
)
risk_kpis_1[3].metric(
    "Concentracion Top 5",
    format_percentage(concentration_risk.top_5_concentration),
)
risk_kpis_1[4].metric(
    "Concentracion Top 10",
    format_percentage(concentration_risk.top_10_concentration),
)

risk_kpis_2 = st.columns(5)
risk_kpis_2[0].metric(
    "Clientes que explican 50%",
    format_number(concentration_risk.clients_for_50_percent),
)
risk_kpis_2[1].metric(
    "Clientes que explican 70%",
    format_number(concentration_risk.clients_for_70_percent),
)
risk_kpis_2[2].metric(
    "Clientes que explican 80%",
    format_number(concentration_risk.clients_for_80_percent),
)
risk_kpis_2[3].metric(
    "Venta principal cliente",
    format_money(concentration_risk.principal_client_sales),
)
risk_kpis_2[4].metric(
    "Participacion principal cliente",
    format_percentage(concentration_risk.principal_client_share),
)

if concentration_risk.risk_level == "Alto":
    st.warning(concentration_risk.executive_summary)
elif concentration_risk.risk_level == "Medio":
    st.info(concentration_risk.executive_summary)
else:
    st.success(concentration_risk.executive_summary)
st.write(concentration_risk.impact_message)

st.write("**Clientes criticos por concentracion**")
critical_table = concentration_risk.critical_clients[
    [
        "ranking",
        "cliente",
        "venta_total",
        "participacion",
        "participacion_acumulada",
        "nivel_criticidad",
    ]
].copy()
critical_table["venta_total"] = critical_table["venta_total"].map(format_money)
critical_table["participacion"] = critical_table["participacion"].map(format_percentage)
critical_table["participacion_acumulada"] = critical_table[
    "participacion_acumulada"
].map(format_percentage)
critical_table.columns = [
    "Ranking",
    "Cliente",
    "Venta total",
    "Participacion %",
    "Participacion acumulada %",
    "Nivel de criticidad",
]
st.dataframe(critical_table, use_container_width=True, hide_index=True)

st.subheader("Evolucion mensual y alertas comerciales")

trend_kpis_1 = st.columns(4)
trend_kpis_1[0].metric("Clientes en crecimiento", client_trends.growing_clients)
trend_kpis_1[1].metric("Clientes en caida", client_trends.declining_clients)
trend_kpis_1[2].metric("Clientes nuevos", client_trends.new_clients)
trend_kpis_1[3].metric("Clientes inactivos", client_trends.inactive_clients)

trend_kpis_2 = st.columns(3)
trend_kpis_2[0].metric("Alertas criticas", client_trends.critical_alerts)
trend_kpis_2[1].metric("Alertas relevantes", client_trends.relevant_alerts)
trend_kpis_2[2].metric("Oportunidades detectadas", client_trends.opportunities)

st.info(
    f"Se detectan {format_number(client_trends.critical_alerts)} alertas criticas "
    f"y {format_number(client_trends.relevant_alerts)} alertas relevantes. El foco "
    "principal debe estar en clientes de alta participacion que muestran caida o "
    "inactividad reciente, ya que pueden afectar la venta total."
)

monthly_chart = client_trends.monthly_summary.set_index("periodo_visible")[["venta_total"]]
st.caption("Evolucion mensual de venta total")
st.line_chart(monthly_chart, use_container_width=True)

st.write("**Detalle de alertas comerciales**")
critical_tab, relevant_tab, opportunity_tab, inactive_tab, all_clients_tab = st.tabs(
    [
        "Alertas criticas",
        "Alertas relevantes",
        "Oportunidades",
        "Clientes inactivos",
        "Todos los clientes",
    ]
)

with critical_tab:
    critical_alerts = (
        client_trends.client_alerts[
            client_trends.client_alerts["alerta_comercial"] == "Alerta critica"
        ]
        .sort_values(["participacion", "venta_total"], ascending=[False, False])
        .head(20)
    )
    show_alerts_table(critical_alerts, "No se detectaron alertas criticas.")

with relevant_tab:
    relevant_alerts = (
        client_trends.client_alerts[
            client_trends.client_alerts["alerta_comercial"] == "Alerta relevante"
        ]
        .sort_values("venta_total", ascending=False)
        .head(20)
    )
    show_alerts_table(relevant_alerts, "No se detectaron alertas relevantes.")

with opportunity_tab:
    opportunities = (
        client_trends.client_alerts[
            client_trends.client_alerts["alerta_comercial"] == "Oportunidad"
        ]
        .sort_values(
            ["venta_ultimos_3_meses", "variacion_porcentual", "venta_total"],
            ascending=[False, False, False],
            na_position="last",
        )
        .head(20)
    )
    show_alerts_table(opportunities, "No se detectaron oportunidades.")

with inactive_tab:
    st.caption(
        "Ordenados por venta historica para distinguir inactivos relevantes de "
        "inactivos de menor impacto."
    )
    inactive_clients = (
        client_trends.client_alerts[
            client_trends.client_alerts["tendencia"] == "Inactivo"
        ]
        .sort_values("venta_total", ascending=False)
        .head(20)
    )
    show_alerts_table(inactive_clients, "No se detectaron clientes inactivos.")

with all_clients_tab:
    all_clients_top_n = st.selectbox(
        "Top N clientes",
        options=[10, 20, 50, 100, "Todos"],
        index=1,
        key="all_clients_top_n",
    )
    all_clients = client_trends.client_alerts.copy()
    if all_clients_top_n != "Todos":
        all_clients = all_clients.head(all_clients_top_n)
    show_alerts_table(all_clients, "No hay clientes para mostrar.")

with st.expander("Filtros avanzados"):
    alert_options = (
        client_trends.client_alerts["alerta_comercial"].drop_duplicates().tolist()
    )
    trend_options = client_trends.client_alerts["tendencia"].drop_duplicates().tolist()
    advanced_filter_cols = st.columns(3)
    selected_alerts = advanced_filter_cols[0].multiselect(
        "Alerta comercial",
        options=alert_options,
        default=alert_options,
        key="advanced_alert_filter",
    )
    selected_trends = advanced_filter_cols[1].multiselect(
        "Tendencia",
        options=trend_options,
        default=trend_options,
        key="advanced_trend_filter",
    )
    selected_top_n = advanced_filter_cols[2].selectbox(
        "Top N",
        options=[10, 20, 50, 100, "Todos"],
        index=1,
        key="advanced_top_n",
    )
    filtered_alerts = client_trends.client_alerts[
        client_trends.client_alerts["alerta_comercial"].isin(selected_alerts)
        & client_trends.client_alerts["tendencia"].isin(selected_trends)
    ].copy()
    if selected_top_n != "Todos":
        filtered_alerts = filtered_alerts.head(selected_top_n)
    show_alerts_table(filtered_alerts, "No hay resultados para los filtros elegidos.")

st.subheader("Inteligencia de tiempo comercial")
time_kpis = st.columns(4)
time_kpis[0].metric(
    "Recompra esperada atrasada",
    format_number(commercial_time.overdue_clients),
)
time_kpis[1].metric(
    "Dentro de ciclo normal",
    format_number(commercial_time.normal_cycle_clients),
)
time_kpis[2].metric(
    "Confianza alta/media",
    format_number(commercial_time.reliable_clients),
)
time_kpis[3].metric(
    "Historial insuficiente",
    format_number(commercial_time.insufficient_history_clients),
)

st.info(
    "La recompra esperada se estima desde la mediana de los intervalos historicos "
    "entre meses con compra de cada cliente. Es una referencia de gestion "
    "comercial, no una prediccion exacta de compra."
)
if commercial_time.reference_date is not None:
    st.caption(
        "Fecha de corte del calculo: "
        f"{format_date(commercial_time.reference_date)} (ultima fecha valida del archivo)."
    )
if commercial_time.clients.empty:
    st.info("No existe historial suficiente para calcular ciclos de recompra.")
else:
    st.caption(
        "Use los filtros para revisar clientes por estado de recompra, vendedor "
        "o nombre de cliente."
    )
    time_filter_row_1 = st.columns(3)
    selected_repurchase_category = time_filter_row_1[0].selectbox(
        "Categoria de recompra",
        options=[
            "Todos",
            "Recompra esperada atrasada",
            "Dentro de ciclo normal",
            "Confianza alta/media",
            "Historial insuficiente",
        ],
        key="time_repurchase_category_filter",
    )
    time_seller_options = sorted(
        commercial_time.clients["vendedor_responsable_sugerido"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    selected_time_pattern = time_filter_row_1[1].selectbox(
        "Lectura comercial del patron",
        options=[
            "Todos",
            "Ciclo consistente",
            "Ciclo razonable",
            "Patrón irregular",
            "Historial insuficiente",
            "Compras concentradas",
        ],
        key="time_commercial_pattern_filter",
    )
    selected_time_seller = time_filter_row_1[2].selectbox(
        "Vendedor responsable sugerido",
        options=["Todos", *time_seller_options],
        key="time_seller_filter",
    )
    time_filter_row_2 = st.columns(2)
    selected_time_confidence = time_filter_row_2[0].selectbox(
        "Confianza",
        options=["Todos", "Alta", "Media", "Baja", "Insuficiente"],
        key="time_confidence_filter",
    )
    time_client_search = time_filter_row_2[1].text_input(
        "Buscar cliente",
        placeholder="Buscar cliente por nombre...",
        key="time_client_search",
    )

    filtered_time_clients = commercial_time.clients.copy()
    if selected_repurchase_category == "Recompra esperada atrasada":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["recompra_atrasada"]
        ]
    elif selected_repurchase_category == "Dentro de ciclo normal":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["dentro_ciclo_normal"]
        ]
    elif selected_repurchase_category == "Confianza alta/media":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["confianza_recompra"].isin(["Alta", "Media"])
        ]
    elif selected_repurchase_category == "Historial insuficiente":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["confianza_recompra"] == "Insuficiente"
        ]

    if selected_time_seller != "Todos":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["vendedor_responsable_sugerido"]
            == selected_time_seller
        ]
    if selected_time_pattern != "Todos":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["lectura_comercial_patron"]
            == selected_time_pattern
        ]
    if selected_time_confidence != "Todos":
        filtered_time_clients = filtered_time_clients[
            filtered_time_clients["confianza_recompra"]
            == selected_time_confidence
        ]
    normalized_time_search = normalize_search_text(time_client_search).strip()
    if normalized_time_search:
        time_client_matches = filtered_time_clients["cliente"].map(
            normalize_search_text
        ).str.contains(normalized_time_search, regex=False, na=False)
        filtered_time_clients = filtered_time_clients[time_client_matches]

    filtered_time_clients = filtered_time_clients.sort_values(
        ["recompra_atrasada", "dias_atraso", "venta_total"],
        ascending=[False, False, False],
        kind="stable",
    )
    if filtered_time_clients.empty:
        st.info("No hay clientes que coincidan con los filtros seleccionados.")
    else:
        st.dataframe(
            format_commercial_time_table(filtered_time_clients),
            use_container_width=True,
            hide_index=True,
        )

st.subheader("Guia de priorizacion comercial")

agenda_kpis = st.columns(5)
agenda_kpis[0].metric(
    "Revision prioritaria",
    format_number(commercial_agenda.high_priority_actions),
)
agenda_kpis[1].metric(
    "Seguimiento sugerido",
    format_number(commercial_agenda.medium_priority_actions),
)
agenda_kpis[2].metric(
    "Monitoreo",
    format_number(commercial_agenda.low_priority_actions),
)
agenda_kpis[3].metric(
    "Clientes sugeridos para revision prioritaria",
    format_number(commercial_agenda.immediate_actions),
)
agenda_kpis[4].metric(
    "Clientes sugeridos para seguimiento",
    format_number(commercial_agenda.this_week_actions),
)

st.info(
    "La guia identifica clientes que deberian revisarse comercialmente por "
    "concentracion, caida, inactividad u oportunidad de desarrollo. Estas "
    "sugerencias deben validarse contra el CRM antes de ejecutar acciones."
)

st.caption(
    "Las prioridades se calculan desde el informe de ventas. Antes de ejecutar "
    "acciones, validar en CRM si el cliente ya tiene seguimiento, llamada, "
    "cotizacion o tarea abierta."
)

st.write("**Clientes sugeridos para revision comercial**")
agenda_with_seller = ensure_agenda_semantic_columns(commercial_agenda.agenda)
commercial_time_for_export = commercial_time.clients.copy()
if not commercial_time_for_export.empty and "participacion" not in commercial_time_for_export:
    commercial_time_for_export = commercial_time_for_export.merge(
        client_analysis.ranking[["cliente", "participacion"]],
        on="cliente",
        how="left",
    )
export_summary = pd.DataFrame(
    [
        {"Indicador": "Periodo analizado", "Valor": period_detail["label"]},
        {"Indicador": "Nivel detectado", "Valor": f"Nivel {level.level}"},
        {"Indicador": "Calidad general de data", "Valor": general_quality},
        {"Indicador": "Filas analizadas", "Valor": format_number(len(df))},
        {
            "Indicador": "Venta total",
            "Valor": format_money(profitability_coverage.total_sales),
        },
        {
            "Indicador": "Clientes unicos",
            "Valor": format_number(client_analysis.total_clients),
        },
        {
            "Indicador": "Concentracion Top 5",
            "Valor": format_percentage(client_analysis.top_5_concentration),
        },
        {
            "Indicador": "Concentracion Top 10",
            "Valor": format_percentage(client_analysis.top_10_concentration),
        },
        {
            "Indicador": "Clientes que explican 80%",
            "Valor": format_number(client_analysis.clients_for_80_percent),
        },
        {
            "Indicador": "Riesgo de concentracion",
            "Valor": concentration_risk.risk_level,
        },
        {
            "Indicador": "Alertas criticas",
            "Valor": format_number(client_trends.critical_alerts),
        },
        {
            "Indicador": "Alertas relevantes",
            "Valor": format_number(client_trends.relevant_alerts),
        },
        {
            "Indicador": "Oportunidades",
            "Valor": format_number(client_trends.opportunities),
        },
        {
            "Indicador": "Clientes inactivos",
            "Valor": format_number(client_trends.inactive_clients),
        },
        {
            "Indicador": "Revision prioritaria",
            "Valor": format_number(commercial_agenda.high_priority_actions),
        },
        {
            "Indicador": "Seguimiento sugerido",
            "Valor": format_number(commercial_agenda.medium_priority_actions),
        },
        {
            "Indicador": "Recompra esperada atrasada",
            "Valor": format_number(commercial_time.overdue_clients),
        },
        {
            "Indicador": "Clientes dentro de ciclo normal",
            "Valor": format_number(commercial_time.normal_cycle_clients),
        },
        {
            "Indicador": "Confianza recompra alta/media",
            "Valor": format_number(commercial_time.reliable_clients),
        },
        {
            "Indicador": "Vendedores identificados",
            "Valor": format_number(
                agenda_with_seller.loc[
                    agenda_with_seller["vendedor_responsable_sugerido"]
                    != "Sin vendedor identificado",
                    "vendedor_responsable_sugerido",
                ].nunique()
            ),
        },
    ]
)
commercial_excel = build_commercial_management_excel(
    export_summary,
    agenda_with_seller,
    client_trends.client_alerts,
    client_analysis.ranking,
    commercial_time_for_export,
)
pdf_summary = {
    "period_label": period_detail["label"],
    "emission_date": pd.Timestamp.today().strftime("%d/%m/%Y"),
    "level_label": f"Nivel {level.level}",
    "general_quality": general_quality,
    "total_sales": profitability_coverage.total_sales,
    "total_clients": client_analysis.total_clients,
    "top_5_concentration": client_analysis.top_5_concentration,
    "top_10_concentration": client_analysis.top_10_concentration,
    "clients_for_80_percent": client_analysis.clients_for_80_percent,
    "risk_level": concentration_risk.risk_level,
    "critical_alerts": client_trends.critical_alerts,
    "relevant_alerts": client_trends.relevant_alerts,
    "opportunities": client_trends.opportunities,
    "inactive_clients": client_trends.inactive_clients,
    "high_priority_actions": commercial_agenda.high_priority_actions,
    "medium_priority_actions": commercial_agenda.medium_priority_actions,
    "low_priority_actions": commercial_agenda.low_priority_actions,
    "overdue_clients": commercial_time.overdue_clients,
    "normal_cycle_clients": commercial_time.normal_cycle_clients,
    "reliable_clients": commercial_time.reliable_clients,
    "insufficient_history_clients": commercial_time.insufficient_history_clients,
}
commercial_pdf = build_executive_clients_pdf(
    summary=pdf_summary,
    ranking=client_analysis.ranking,
    agenda=agenda_with_seller,
    commercial_time_clients=commercial_time_for_export,
    logo_path=LOGO_PATH,
)
st.download_button(
    "Descargar Excel para gestión comercial",
    data=commercial_excel,
    file_name="kappo_guia_comercial_clientes.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
st.download_button(
    "Descargar PDF ejecutivo",
    data=commercial_pdf,
    file_name="kappo_analisis_ejecutivo_clientes.pdf",
    mime="application/pdf",
    use_container_width=True,
)
seller_options = sorted(
    agenda_with_seller["vendedor_responsable_sugerido"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
selected_seller = st.selectbox(
    "Vendedor responsable sugerido",
    options=["Todos", *seller_options],
    key="agenda_seller_filter",
)
client_search = st.text_input(
    "Buscar cliente",
    placeholder="Buscar cliente por nombre...",
    key="agenda_client_search",
    label_visibility="collapsed",
)
filtered_agenda = agenda_with_seller
if selected_seller != "Todos":
    filtered_agenda = filtered_agenda[
        filtered_agenda["vendedor_responsable_sugerido"] == selected_seller
    ]
normalized_client_search = normalize_search_text(client_search).strip()
if normalized_client_search:
    client_matches = filtered_agenda["cliente"].map(normalize_search_text).str.contains(
        normalized_client_search,
        regex=False,
        na=False,
    )
    filtered_agenda = filtered_agenda[client_matches]

high_agenda_tab, medium_agenda_tab, opportunity_agenda_tab, all_agenda_tab = st.tabs(
    [
        "Revision prioritaria",
        "Seguimiento sugerido",
        "Oportunidades",
        "Todos",
    ]
)

with high_agenda_tab:
    high_agenda = filtered_agenda[
        filtered_agenda["prioridad_gestion"] == "Alta"
    ].head(20)
    show_agenda_table(high_agenda, "No hay clientes para revision prioritaria.")

with medium_agenda_tab:
    medium_agenda = filtered_agenda[
        (filtered_agenda["prioridad_gestion"] == "Media")
        & (filtered_agenda["alerta_comercial"] != "Oportunidad")
    ].head(20)
    show_agenda_table(medium_agenda, "No hay clientes con seguimiento sugerido.")

with opportunity_agenda_tab:
    opportunity_agenda = filtered_agenda[
        filtered_agenda["alerta_comercial"] == "Oportunidad"
    ].head(20)
    show_agenda_table(opportunity_agenda, "No hay oportunidades sugeridas.")

with all_agenda_tab:
    agenda_top_n = st.selectbox(
        "Top N clientes",
        options=[10, 20, 50, 100, "Todos"],
        index=1,
        key="agenda_top_n",
    )
    all_agenda = filtered_agenda.copy()
    if agenda_top_n != "Todos":
        all_agenda = all_agenda.head(agenda_top_n)
    show_agenda_table(all_agenda, "No hay sugerencias comerciales para mostrar.")

st.divider()
st.subheader("Respaldo tecnico")

with st.expander("Columnas originales"):
    st.dataframe(
        pd.DataFrame({"columna_original": list(df.columns)}),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Columnas normalizadas"):
    st.dataframe(
        pd.DataFrame(
            {
                "original": list(normalization_map.keys()),
                "normalizada": list(normalization_map.values()),
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

found_rows = [
    {"campo_clave": field.label, "columna_detectada": field.detected_column}
    for field in detection.fields
    if field.detected_column
]
missing_rows = [
    {"campo_clave": field.label, "sinonimos_buscados": ", ".join(field.aliases)}
    for field in detection.fields
    if not field.detected_column
]

with st.expander("Columnas clave encontradas"):
    if found_rows:
        st.dataframe(pd.DataFrame(found_rows), use_container_width=True, hide_index=True)
    else:
        st.write("No se detectaron columnas clave.")

with st.expander("Columnas clave faltantes"):
    if missing_rows:
        st.dataframe(pd.DataFrame(missing_rows), use_container_width=True, hide_index=True)
    else:
        st.success("No faltan columnas clave para el maximo nivel definido.")

period_rows = [
    {
        "metrica": "Fecha minima",
        "valor": "N/D"
        if period_detail["min_date"] is None
        else format_date(period_detail["min_date"]),
    },
    {
        "metrica": "Fecha maxima",
        "valor": "N/D"
        if period_detail["max_date"] is None
        else format_date(period_detail["max_date"]),
    },
    {
        "metrica": "Filas con fecha valida",
        "valor": format_number(period_detail["valid_date_rows"]),
    },
    {
        "metrica": "Filas sin fecha valida",
        "valor": format_number(period_detail["invalid_date_rows"]),
    },
]
with st.expander("Detalle de periodo"):
    st.dataframe(pd.DataFrame(period_rows), use_container_width=True, hide_index=True)

document_metric_rows = [
    {"metrica": "Documentos unicos", "valor": format_number(document_metrics.total_unique_documents)},
    {
        "metrica": "Documentos multilinea detectados",
        "valor": format_number(document_metrics.multiline_documents),
    },
    {
        "metrica": "Posibles duplicados exactos detectados",
        "valor": format_number(document_metrics.possible_exact_duplicates),
    },
    {
        "metrica": "Filas involucradas en posibles duplicados exactos",
        "valor": format_number(document_metrics.possible_exact_duplicate_rows),
    },
]
with st.expander("Metricas completas de documentos"):
    st.dataframe(pd.DataFrame(document_metric_rows), use_container_width=True, hide_index=True)

render_dataframe_expander(
    "Ejemplos de posibles duplicados exactos",
    duplicate_examples,
    "No se detectaron ejemplos de posibles duplicados exactos.",
)

sku_metric_rows = [
    {"metrica": "Filas totales", "valor": format_number(sku_coverage.total_rows)},
    {"metrica": "Filas con SKU valido", "valor": format_number(sku_coverage.valid_sku_rows)},
    {"metrica": "Filas con SKU vacio", "valor": format_number(sku_coverage.empty_sku_rows)},
    {
        "metrica": "% filas con SKU valido",
        "valor": format_percentage(sku_coverage.valid_sku_row_percentage),
    },
    {"metrica": "Venta con SKU valido", "valor": format_money(sku_coverage.valid_sku_sales)},
    {"metrica": "Venta con SKU vacio", "valor": format_money(sku_coverage.empty_sku_sales)},
    {
        "metrica": "% venta con SKU valido",
        "valor": format_percentage(sku_coverage.valid_sku_sales_percentage),
    },
    {
        "metrica": "% venta con SKU vacio",
        "valor": format_percentage(sku_coverage.empty_sku_sales_percentage),
    },
    {
        "metrica": "Filas SKU vacio con costo/margen valido",
        "valor": format_number(sku_coverage.empty_sku_with_profitability_rows),
    },
    {
        "metrica": "Venta SKU vacio con costo/margen valido",
        "valor": format_money(sku_coverage.empty_sku_with_profitability_sales),
    },
    {
        "metrica": "Margen/utilidad asociado a SKU vacio",
        "valor": "N/D"
        if sku_coverage.empty_sku_profitability_amount is None
        else format_money(sku_coverage.empty_sku_profitability_amount),
    },
]
with st.expander("Metricas completas de cobertura SKU"):
    st.dataframe(pd.DataFrame(sku_metric_rows), use_container_width=True, hide_index=True)

render_dataframe_expander(
    "Ejemplos de lineas con SKU vacio",
    empty_sku_examples,
    "No se detectaron lineas con SKU vacio.",
)

profitability_metric_rows = [
    {"metrica": "Filas totales", "valor": format_number(profitability_coverage.total_rows)},
    {
        "metrica": "Filas con monto venta valido",
        "valor": format_number(profitability_coverage.valid_sales_amount_rows),
    },
    {"metrica": "Filas con costo valido", "valor": format_number(profitability_coverage.valid_cost_rows)},
    {
        "metrica": "Filas con margen/utilidad valido",
        "valor": format_number(profitability_coverage.valid_margin_rows),
    },
    {"metrica": "Filas con costo cero", "valor": format_number(profitability_coverage.zero_cost_rows)},
    {"metrica": "Filas con costo nulo", "valor": format_number(profitability_coverage.null_cost_rows)},
    {"metrica": "Filas con margen nulo", "valor": format_number(profitability_coverage.null_margin_rows)},
    {
        "metrica": "Filas con margen negativo",
        "valor": format_number(profitability_coverage.negative_margin_rows),
    },
    {"metrica": "Venta total", "valor": format_money(profitability_coverage.total_sales)},
    {
        "metrica": "Venta con costo valido",
        "valor": format_money(profitability_coverage.sales_with_valid_cost),
    },
    {
        "metrica": "Venta sin costo valido",
        "valor": format_money(profitability_coverage.sales_without_valid_cost),
    },
    {
        "metrica": "% venta con costo valido",
        "valor": format_percentage(profitability_coverage.valid_cost_sales_percentage),
    },
    {
        "metrica": "% venta sin costo valido",
        "valor": format_percentage(profitability_coverage.without_valid_cost_sales_percentage),
    },
    {
        "metrica": "Margen/utilidad total",
        "valor": "N/D"
        if profitability_coverage.total_margin_amount is None
        else format_money(profitability_coverage.total_margin_amount),
    },
    {
        "metrica": "Margen comercial calculado",
        "valor": "N/D"
        if profitability_coverage.calculated_commercial_margin is None
        else format_percentage(profitability_coverage.calculated_commercial_margin),
    },
]
with st.expander("Metricas completas de cobertura costo/margen"):
    st.dataframe(pd.DataFrame(profitability_metric_rows), use_container_width=True, hide_index=True)

render_dataframe_expander(
    "Ejemplos de lineas sin costo/margen valido",
    missing_profitability_examples,
    "No se detectaron lineas sin costo/margen valido.",
)

dataset_rows = [
    {"vista": name, "filas": len(dataset)}
    for name, dataset in analysis_datasets.items()
]
with st.expander("Vistas de analisis"):
    st.dataframe(pd.DataFrame(dataset_rows), use_container_width=True, hide_index=True)

with st.expander("Advertencias tecnicas de calidad"):
    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("No se detectaron advertencias criticas en esta revision inicial.")

with st.expander("Vista previa de datos"):
    st.dataframe(df.head(50), use_container_width=True)

with st.expander("Vista previa con columnas normalizadas"):
    st.dataframe(normalized_df.head(50), use_container_width=True)
