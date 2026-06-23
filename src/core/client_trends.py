from dataclasses import dataclass

import pandas as pd

from src.core.client_analysis import ClientAnalysisResult
from src.models import ColumnDetectionResult


@dataclass(frozen=True)
class ClientTrendAnalysisResult:
    detected_months: int
    first_month: str | None
    last_month: str | None
    last_3_months_sales: float
    previous_3_months_sales: float
    total_variation_percentage: float | None
    growing_clients: int
    declining_clients: int
    new_clients: int
    inactive_clients: int
    critical_alerts: int
    relevant_alerts: int
    opportunities: int
    monthly_summary: pd.DataFrame
    client_alerts: pd.DataFrame


def _detected_column(detection: ColumnDetectionResult, key: str) -> str | None:
    field = detection.get(key)
    return field.detected_column if field else None


def build_client_trend_analysis(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
    client_analysis: ClientAnalysisResult,
) -> ClientTrendAnalysisResult:
    client_column = _detected_column(detection, "cliente")
    date_column = _detected_column(detection, "fecha")
    amount_column = _detected_column(detection, "monto_venta")
    required = [client_column, date_column, amount_column]
    if any(not column or column not in df.columns for column in required):
        return _empty_result()

    working_df = df[[client_column, date_column, amount_column]].copy()
    working_df[client_column] = working_df[client_column].astype("string").str.strip()
    working_df[date_column] = pd.to_datetime(
        working_df[date_column], errors="coerce", dayfirst=True
    )
    working_df[amount_column] = pd.to_numeric(working_df[amount_column], errors="coerce")
    working_df = working_df.dropna(subset=[client_column, date_column, amount_column])
    working_df = working_df[working_df[client_column].ne("")]
    if working_df.empty:
        return _empty_result()

    working_df["periodo"] = working_df[date_column].dt.to_period("M")
    first_period = working_df["periodo"].min()
    last_period = working_df["periodo"].max()
    all_periods = pd.period_range(first_period, last_period, freq="M")

    monthly_client = (
        working_df.groupby([client_column, "periodo"])[amount_column]
        .sum()
        .unstack(fill_value=0)
        .reindex(columns=all_periods, fill_value=0)
    )
    monthly_total = monthly_client.sum(axis=0)
    active_clients = monthly_client.gt(0).sum(axis=0)
    monthly_summary = pd.DataFrame(
        {
            "periodo": [period.strftime("%Y-%m") for period in all_periods],
            "periodo_visible": [period.strftime("%m/%Y") for period in all_periods],
            "venta_total": monthly_total.to_numpy(dtype=float),
            "clientes_activos": active_clients.to_numpy(dtype=int),
        }
    )

    last_3_periods = all_periods[-3:]
    previous_3_periods = all_periods[-6:-3]
    earlier_periods = all_periods[:-3]
    last_3_sales = monthly_client[last_3_periods].sum(axis=1)
    previous_3_sales = monthly_client[previous_3_periods].sum(axis=1)
    earlier_positive = (
        monthly_client[earlier_periods].gt(0).any(axis=1)
        if len(earlier_periods)
        else pd.Series(False, index=monthly_client.index)
    )
    recent_positive = monthly_client[last_3_periods].gt(0).any(axis=1)

    ranking_data = client_analysis.ranking.set_index("cliente")
    rows: list[dict[str, object]] = []
    median_sales = client_analysis.median_sales_per_client
    for client, monthly_values in monthly_client.iterrows():
        total_sales = float(monthly_values.sum())
        current_sales = float(last_3_sales.loc[client])
        previous_sales = float(previous_3_sales.loc[client])
        absolute_variation = current_sales - previous_sales
        percentage_variation = (
            absolute_variation / previous_sales if previous_sales > 0 else None
        )
        purchase_periods = monthly_values[monthly_values > 0].index
        months_with_purchase = len(purchase_periods)
        last_purchase = purchase_periods.max() if months_with_purchase else None

        is_new = bool(recent_positive.loc[client] and not earlier_positive.loc[client])
        is_inactive = bool(earlier_positive.loc[client] and not recent_positive.loc[client])
        trend = _classify_trend(
            is_new,
            is_inactive,
            previous_sales,
            percentage_variation,
        )

        ranking_row = ranking_data.loc[client]
        participation = float(ranking_row["participacion"])
        rank = int(ranking_row["ranking"])
        is_critical = rank <= client_analysis.clients_for_50_percent
        is_strategic = rank <= client_analysis.clients_for_80_percent
        alert, recommendation = _classify_alert(
            trend=trend,
            participation=participation,
            percentage_variation=percentage_variation,
            is_critical=is_critical,
            is_strategic=is_strategic,
            total_sales=total_sales,
            median_sales=median_sales,
            months_with_purchase=months_with_purchase,
            current_sales=current_sales,
            previous_sales=previous_sales,
        )

        rows.append(
            {
                "cliente": client,
                "venta_total": total_sales,
                "participacion": participation,
                "venta_ultimos_3_meses": current_sales,
                "venta_3_meses_anteriores": previous_sales,
                "variacion_absoluta": absolute_variation,
                "variacion_porcentual": percentage_variation,
                "meses_con_compra": months_with_purchase,
                "ultimo_mes_con_compra": (
                    last_purchase.strftime("%m/%Y") if last_purchase else "Sin compra"
                ),
                "cliente_critico": is_critical,
                "tendencia": trend,
                "alerta_comercial": alert,
                "recomendacion_sugerida": recommendation,
            }
        )

    client_alerts = pd.DataFrame(rows)
    priority = {
        "Alerta critica": 0,
        "Alerta relevante": 1,
        "Oportunidad": 2,
        "Sin alerta": 3,
    }
    client_alerts["prioridad_alerta"] = client_alerts["alerta_comercial"].map(priority)
    client_alerts["variacion_orden"] = client_alerts["variacion_porcentual"].fillna(0)
    client_alerts = client_alerts.sort_values(
        ["prioridad_alerta", "venta_total", "variacion_orden"],
        ascending=[True, False, True],
        kind="stable",
    ).reset_index(drop=True)
    client_alerts = client_alerts.drop(columns=["prioridad_alerta", "variacion_orden"])

    total_last_3 = float(last_3_sales.sum())
    total_previous_3 = float(previous_3_sales.sum())
    total_variation = (
        (total_last_3 - total_previous_3) / total_previous_3
        if total_previous_3 > 0
        else None
    )

    return ClientTrendAnalysisResult(
        detected_months=len(all_periods),
        first_month=first_period.strftime("%m/%Y"),
        last_month=last_period.strftime("%m/%Y"),
        last_3_months_sales=total_last_3,
        previous_3_months_sales=total_previous_3,
        total_variation_percentage=total_variation,
        growing_clients=int((client_alerts["tendencia"] == "En crecimiento").sum()),
        declining_clients=int((client_alerts["tendencia"] == "En caida").sum()),
        new_clients=int((client_alerts["tendencia"] == "Nuevo").sum()),
        inactive_clients=int((client_alerts["tendencia"] == "Inactivo").sum()),
        critical_alerts=int((client_alerts["alerta_comercial"] == "Alerta critica").sum()),
        relevant_alerts=int((client_alerts["alerta_comercial"] == "Alerta relevante").sum()),
        opportunities=int((client_alerts["alerta_comercial"] == "Oportunidad").sum()),
        monthly_summary=monthly_summary,
        client_alerts=client_alerts,
    )


def _classify_trend(
    is_new: bool,
    is_inactive: bool,
    previous_sales: float,
    percentage_variation: float | None,
) -> str:
    if is_new:
        return "Nuevo"
    if is_inactive:
        return "Inactivo"
    if previous_sales > 0 and percentage_variation is not None:
        if percentage_variation >= 0.20:
            return "En crecimiento"
        if percentage_variation <= -0.20:
            return "En caida"
        return "Estable"
    return "Intermitente"


def _classify_alert(
    *,
    trend: str,
    participation: float,
    percentage_variation: float | None,
    is_critical: bool,
    is_strategic: bool,
    total_sales: float,
    median_sales: float,
    months_with_purchase: int,
    current_sales: float,
    previous_sales: float,
) -> tuple[str, str]:
    is_declining = trend == "En caida"
    is_inactive = trend == "Inactivo"
    decline_over_30 = percentage_variation is not None and percentage_variation <= -0.30

    if (is_critical and (is_declining or is_inactive)) or (
        participation >= 0.01 and decline_over_30
    ):
        recommendation = (
            "Contactar para recuperacion o entender perdida."
            if is_inactive
            else "Revisar causa de caida y priorizar gestion comercial."
        )
        return "Alerta critica", recommendation

    if (is_strategic and (is_declining or is_inactive)) or (
        participation >= 0.01 and current_sales <= 0 and previous_sales > 0
    ):
        recommendation = (
            "Contactar para recuperacion o entender perdida."
            if is_inactive
            else "Revisar causa de caida y priorizar gestion comercial."
        )
        return "Alerta relevante", recommendation

    if trend == "Nuevo" and total_sales >= median_sales:
        return "Oportunidad", "Monitorear continuidad y potencial de desarrollo."
    if trend == "En crecimiento" or (
        months_with_purchase <= 3 and current_sales > previous_sales
    ):
        return (
            "Oportunidad",
            "Evaluar oportunidad de profundizar relacion comercial.",
        )
    if trend == "Estable":
        return "Sin alerta", "Mantener seguimiento."
    return "Sin alerta", "Revisar patron de compra en el seguimiento comercial."


def _empty_result() -> ClientTrendAnalysisResult:
    return ClientTrendAnalysisResult(
        detected_months=0,
        first_month=None,
        last_month=None,
        last_3_months_sales=0.0,
        previous_3_months_sales=0.0,
        total_variation_percentage=None,
        growing_clients=0,
        declining_clients=0,
        new_clients=0,
        inactive_clients=0,
        critical_alerts=0,
        relevant_alerts=0,
        opportunities=0,
        monthly_summary=pd.DataFrame(
            columns=["periodo", "periodo_visible", "venta_total", "clientes_activos"]
        ),
        client_alerts=pd.DataFrame(
            columns=[
                "cliente",
                "venta_total",
                "participacion",
                "venta_ultimos_3_meses",
                "venta_3_meses_anteriores",
                "variacion_absoluta",
                "variacion_porcentual",
                "meses_con_compra",
                "ultimo_mes_con_compra",
                "cliente_critico",
                "tendencia",
                "alerta_comercial",
                "recomendacion_sugerida",
            ]
        ),
    )
