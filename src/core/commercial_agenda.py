from dataclasses import dataclass

import pandas as pd

from src.models import ColumnDetectionResult


@dataclass(frozen=True)
class CommercialAgendaResult:
    high_priority_actions: int
    medium_priority_actions: int
    low_priority_actions: int
    immediate_actions: int
    this_week_actions: int
    agenda: pd.DataFrame


def build_commercial_agenda(
    client_alerts: pd.DataFrame,
    median_client_sales: float,
    sales_df: pd.DataFrame | None = None,
    detection: ColumnDetectionResult | None = None,
) -> CommercialAgendaResult:
    if client_alerts.empty:
        return _empty_result()

    agenda = client_alerts.copy()
    principal_client = agenda.loc[agenda["participacion"].idxmax(), "cliente"]
    assignments = agenda.apply(
        lambda row: _assign_action(
            row,
            median_client_sales=median_client_sales,
            is_principal=row["cliente"] == principal_client,
        ),
        axis=1,
        result_type="expand",
    )
    assignments.columns = [
        "prioridad_gestion",
        "tipo_sugerencia",
        "plazo_sugerido",
        "motivo_prioridad",
    ]
    agenda = pd.concat([agenda, assignments], axis=1)
    agenda["por_que_importa"] = agenda.apply(_build_why_it_matters, axis=1)
    agenda["motivo_comercial"] = agenda["por_que_importa"]
    agenda["validacion_requerida_crm"] = (
        "Revisar si existe gestion, llamada, cotizacion o tarea abierta en CRM."
    )
    seller_by_client = _build_suggested_seller_by_client(sales_df, detection)
    agenda["vendedor_responsable_sugerido"] = (
        agenda["cliente"]
        .astype("string")
        .str.strip()
        .map(seller_by_client)
        .fillna("Sin vendedor identificado")
    )

    priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
    deadline_order = {
        "Inmediato": 0,
        "Esta semana": 1,
        "Proximos 30 dias": 2,
        "Seguimiento mensual": 3,
    }
    alert_order = {
        "Alerta critica": 0,
        "Alerta relevante": 1,
        "Oportunidad": 2,
        "Sin alerta": 3,
    }
    agenda["_prioridad"] = agenda["prioridad_gestion"].map(priority_order)
    agenda["_plazo"] = agenda["plazo_sugerido"].map(deadline_order)
    agenda["_alerta"] = agenda["alerta_comercial"].map(alert_order)
    agenda = agenda.sort_values(
        ["_prioridad", "_plazo", "_alerta", "venta_total"],
        ascending=[True, True, True, False],
        kind="stable",
    ).drop(columns=["_prioridad", "_plazo", "_alerta"])
    agenda = agenda.reset_index(drop=True)

    return CommercialAgendaResult(
        high_priority_actions=int((agenda["prioridad_gestion"] == "Alta").sum()),
        medium_priority_actions=int((agenda["prioridad_gestion"] == "Media").sum()),
        low_priority_actions=int((agenda["prioridad_gestion"] == "Baja").sum()),
        immediate_actions=int((agenda["plazo_sugerido"] == "Inmediato").sum()),
        this_week_actions=int((agenda["plazo_sugerido"] == "Esta semana").sum()),
        agenda=agenda,
    )


def _build_suggested_seller_by_client(
    sales_df: pd.DataFrame | None,
    detection: ColumnDetectionResult | None,
) -> dict[str, str]:
    if sales_df is None or sales_df.empty or detection is None:
        return {}

    client_field = detection.get("cliente")
    date_field = detection.get("fecha")
    seller_field = detection.get("vendedor")
    client_column = client_field.detected_column if client_field else None
    date_column = date_field.detected_column if date_field else None
    seller_column = seller_field.detected_column if seller_field else None
    required_columns = {client_column, date_column, seller_column}
    if None in required_columns or not required_columns.issubset(sales_df.columns):
        return {}

    sales = sales_df[[client_column, date_column, seller_column]].copy()
    sales["_cliente"] = sales[client_column].astype("string").str.strip()
    sales["_fecha"] = pd.to_datetime(sales[date_column], errors="coerce", dayfirst=True)
    sales["_vendedor"] = sales[seller_column].astype("string").str.strip()
    sales.loc[
        sales["_vendedor"].isna() | sales["_vendedor"].eq(""), "_vendedor"
    ] = pd.NA
    sales = sales[sales["_cliente"].notna() & sales["_cliente"].ne("")]
    sales = sales[sales["_fecha"].notna()]
    if sales.empty:
        return {}

    latest_date = sales.groupby("_cliente")["_fecha"].transform("max")
    latest_sales = sales[sales["_fecha"].eq(latest_date)]
    latest_sellers = (
        latest_sales.dropna(subset=["_vendedor"])
        .drop_duplicates(subset=["_cliente"], keep="last")
        .set_index("_cliente")["_vendedor"]
    )
    return latest_sellers.astype(str).to_dict()


def _assign_action(
    row: pd.Series,
    *,
    median_client_sales: float,
    is_principal: bool,
) -> tuple[str, str, str, str]:
    alert = row["alerta_comercial"]
    trend = row["tendencia"]
    participation = float(row["participacion"])
    total_sales = float(row["venta_total"])
    variation = row["variacion_porcentual"]
    significant_decline = pd.notna(variation) and float(variation) <= -0.30
    negative_trend = trend in {"En caida", "Inactivo"}

    high_priority = (
        alert == "Alerta critica"
        or (bool(row.get("cliente_critico", False)) and negative_trend)
        or (participation >= 0.01 and significant_decline)
        or (is_principal and negative_trend)
    )
    medium_priority = (
        alert == "Alerta relevante"
        or (trend == "Inactivo" and total_sales >= median_client_sales)
        or (
            alert == "Oportunidad"
            and trend in {"Nuevo", "En crecimiento"}
            and total_sales >= median_client_sales
        )
    )
    priority = "Alta" if high_priority else "Media" if medium_priority else "Baja"

    if alert == "Alerta critica" and trend == "En caida":
        return (
            "Alta",
            "Revisar cliente critico",
            "Inmediato",
            "Cliente de alta participacion con caida reciente.",
        )
    if alert == "Alerta critica" and trend == "Inactivo":
        return (
            "Alta",
            "Validar recuperacion de cliente relevante",
            "Inmediato",
            "Cliente relevante sin compra reciente.",
        )
    if priority == "Alta":
        return (
            "Alta",
            "Revisar cliente critico",
            "Inmediato",
            "Cliente de alta participacion con riesgo comercial reciente.",
        )
    if alert == "Alerta relevante" and trend == "En caida":
        return (
            "Media",
            "Investigar caida de compra",
            "Esta semana",
            "Cliente con venta relevante y disminucion reciente.",
        )
    if alert == "Alerta relevante" and trend == "Inactivo":
        return (
            "Media",
            "Validar recuperacion de cliente relevante",
            "Esta semana",
            "Cliente relevante sin compra reciente.",
        )
    if alert == "Oportunidad" and trend == "En crecimiento":
        return (
            priority,
            "Evaluar profundizacion comercial",
            "Proximos 30 dias",
            "Cliente con aumento reciente de compras.",
        )
    if alert == "Oportunidad" and trend == "Nuevo":
        return (
            priority,
            "Evaluar desarrollo comercial",
            "Proximos 30 dias",
            "Cliente nuevo con potencial de continuidad.",
        )
    if alert == "Oportunidad":
        return (
            priority,
            "Evaluar desarrollo comercial",
            "Proximos 30 dias",
            "Cliente con oportunidad de desarrollo comercial.",
        )
    if trend == "Estable":
        return (
            priority,
            "Mantener seguimiento",
            "Seguimiento mensual",
            "Cliente estable sin cambios comerciales relevantes.",
        )
    return (
        priority,
        "Mantener seguimiento",
        "Seguimiento mensual",
        "Cliente de bajo impacto sin alerta comercial prioritaria.",
    )


def _build_why_it_matters(row: pd.Series) -> str:
    trend = row["tendencia"]
    participation = float(row["participacion"])
    variation = row.get("variacion_porcentual")
    recent_sales = float(row.get("venta_ultimos_3_meses", 0) or 0)
    last_purchase = row.get("ultimo_mes_con_compra", "sin fecha")
    participation_label = f"{participation:.1%}".replace(".", ",")

    if trend == "En caida" and pd.notna(variation):
        decline_label = f"{abs(float(variation)):.1%}".replace(".", ",")
        return (
            f"Representa {participation_label} de la venta y cayo "
            f"{decline_label} en los ultimos 3 meses."
        )
    if trend == "Inactivo":
        return (
            f"Representa {participation_label} de la venta y no compra desde "
            f"{last_purchase}."
        )
    if trend in {"Nuevo", "En crecimiento"}:
        recent_sales_label = "$" + f"{recent_sales:,.0f}".replace(",", ".")
        return (
            f"Cliente {trend.lower()} con {recent_sales_label} de venta reciente "
            "y potencial de desarrollo."
        )
    if trend == "Estable":
        return f"Mantiene una participacion de {participation_label} sin cambios relevantes."
    return f"Participacion de {participation_label} con comportamiento intermitente."


def _empty_result() -> CommercialAgendaResult:
    return CommercialAgendaResult(
        high_priority_actions=0,
        medium_priority_actions=0,
        low_priority_actions=0,
        immediate_actions=0,
        this_week_actions=0,
        agenda=pd.DataFrame(),
    )
