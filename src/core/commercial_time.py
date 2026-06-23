from dataclasses import dataclass

import pandas as pd

from src.models import ColumnDetectionResult


@dataclass(frozen=True)
class CommercialTimeResult:
    overdue_clients: int
    normal_cycle_clients: int
    reliable_clients: int
    insufficient_history_clients: int
    reference_date: pd.Timestamp | None
    clients: pd.DataFrame


def build_commercial_time_intelligence(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
    reference_date: pd.Timestamp | None = None,
) -> CommercialTimeResult:
    client_column = _detected_column(detection, "cliente")
    date_column = _detected_column(detection, "fecha")
    amount_column = _detected_column(detection, "monto_venta")
    seller_column = _detected_column(detection, "vendedor")
    document_column = _detected_column(detection, "documento_folio")
    required = [client_column, date_column, amount_column]
    if any(not column or column not in df.columns for column in required):
        return _empty_result()

    selected_columns = [client_column, date_column, amount_column]
    for optional_column in [seller_column, document_column]:
        if optional_column and optional_column in df.columns:
            selected_columns.append(optional_column)

    sales = df[selected_columns].copy()
    sales["_cliente"] = sales[client_column].astype("string").str.strip()
    sales["_fecha"] = pd.to_datetime(
        sales[date_column], errors="coerce", dayfirst=True
    ).dt.normalize()
    sales["_monto"] = pd.to_numeric(sales[amount_column], errors="coerce")
    sales = sales[
        sales["_cliente"].notna()
        & sales["_cliente"].ne("")
        & sales["_fecha"].notna()
        & sales["_monto"].notna()
        & sales["_monto"].gt(0)
    ]
    if sales.empty:
        return _empty_result()

    cutoff_date = (
        pd.Timestamp(reference_date).normalize()
        if reference_date is not None
        else sales["_fecha"].max()
    )
    rows = [
        _build_client_row(
            client,
            client_sales,
            cutoff_date,
            seller_column,
            document_column,
        )
        for client, client_sales in sales.groupby("_cliente", sort=False)
    ]
    clients = pd.DataFrame(rows)
    confidence_order = {"Alta": 0, "Media": 1, "Baja": 2, "Insuficiente": 3}
    clients["_confianza"] = clients["confianza_recompra"].map(confidence_order)
    clients = clients.sort_values(
        ["dias_atraso", "_confianza", "venta_total"],
        ascending=[False, True, False],
        kind="stable",
    ).drop(columns=["_confianza"])
    clients = clients.reset_index(drop=True)

    return CommercialTimeResult(
        overdue_clients=int(clients["recompra_atrasada"].sum()),
        normal_cycle_clients=int(clients["dentro_ciclo_normal"].sum()),
        reliable_clients=int(
            clients["confianza_recompra"].isin(["Alta", "Media"]).sum()
        ),
        insufficient_history_clients=int(
            (clients["confianza_recompra"] == "Insuficiente").sum()
        ),
        reference_date=cutoff_date,
        clients=clients,
    )


def _build_client_row(
    client: str,
    sales: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    seller_column: str | None,
    document_column: str | None,
) -> dict[str, object]:
    purchase_months = sales["_fecha"].dt.to_period("M").drop_duplicates().sort_values()
    month_anchors = purchase_months.dt.to_timestamp()
    intervals = month_anchors.diff().dt.days.dropna()
    intervals = intervals[intervals > 0]
    typical_interval = float(intervals.median()) if not intervals.empty else None
    variability = _robust_interval_variability(intervals, typical_interval)
    purchase_month_count = len(purchase_months)
    document_purchase_count = _count_purchases(sales, document_column)
    confidence = _classify_confidence(
        purchase_month_count,
        purchase_month_count,
        len(intervals),
        variability,
    )

    first_purchase = sales["_fecha"].min()
    last_purchase = sales["_fecha"].max()
    purchase_window_days = int((last_purchase - first_purchase).days)
    concentrated_purchases = document_purchase_count >= 2 and (
        purchase_month_count == 1 or purchase_window_days <= 30
    )
    commercial_pattern = _build_commercial_pattern(
        confidence,
        concentrated_purchases,
    )
    expected_purchase = (
        last_purchase + pd.to_timedelta(round(typical_interval), unit="D")
        if typical_interval is not None
        else pd.NaT
    )
    overdue_days = (
        max(int((cutoff_date - expected_purchase).days), 0)
        if pd.notna(expected_purchase)
        else 0
    )
    is_overdue = bool(
        pd.notna(expected_purchase)
        and expected_purchase < cutoff_date
        and not concentrated_purchases
    )
    is_normal = bool(
        pd.notna(expected_purchase)
        and expected_purchase >= cutoff_date
        and not concentrated_purchases
    )
    repurchase_category = _build_repurchase_category(
        is_overdue,
        is_normal,
        confidence,
        commercial_pattern,
    )

    return {
        "cliente": client,
        "vendedor_responsable_sugerido": _latest_seller(sales, seller_column),
        "cantidad_compras": purchase_month_count,
        "cantidad_meses_con_compra": purchase_month_count,
        "cantidad_documentos_compra": document_purchase_count,
        "primera_compra": first_purchase,
        "ultima_compra": last_purchase,
        "ultimo_mes_con_compra": last_purchase.strftime("%m/%Y"),
        "dias_desde_ultima_compra": max(int((cutoff_date - last_purchase).days), 0),
        "intervalo_mediano_dias": typical_interval,
        "intervalo_mensual_mediano_dias": typical_interval,
        "variabilidad_intervalo": variability,
        "proxima_compra_esperada": expected_purchase,
        "dias_atraso": overdue_days,
        "categoria_recompra": repurchase_category,
        "confianza_recompra": confidence,
        "lectura_comercial_patron": commercial_pattern,
        "recompra_atrasada": is_overdue,
        "dentro_ciclo_normal": is_normal,
        "compras_concentradas": concentrated_purchases,
        "sugerencia_por_tiempo": _build_time_suggestion(
            commercial_pattern,
            is_overdue,
        ),
        "sugerencia_tiempo_comercial": _build_time_suggestion(
            commercial_pattern,
            is_overdue,
        ),
        "venta_total": float(sales["_monto"].sum()),
    }


def _count_purchases(sales: pd.DataFrame, document_column: str | None) -> int:
    if not document_column or document_column not in sales.columns:
        return int(sales["_fecha"].nunique())

    documents = sales[document_column].astype("string").str.strip()
    valid_documents = documents[documents.notna() & documents.ne("")]
    missing_document_dates = sales.loc[
        documents.isna() | documents.eq(""), "_fecha"
    ].nunique()
    return int(valid_documents.nunique() + missing_document_dates)


def _latest_seller(sales: pd.DataFrame, seller_column: str | None) -> str:
    if not seller_column or seller_column not in sales.columns:
        return "Sin vendedor identificado"
    latest_date = sales["_fecha"].max()
    sellers = sales.loc[sales["_fecha"].eq(latest_date), seller_column]
    sellers = sellers.astype("string").str.strip()
    sellers = sellers[sellers.notna() & sellers.ne("")]
    return str(sellers.iloc[-1]) if not sellers.empty else "Sin vendedor identificado"


def _robust_interval_variability(
    intervals: pd.Series,
    typical_interval: float | None,
) -> float | None:
    if intervals.empty or typical_interval is None or typical_interval <= 0:
        return None
    median_absolute_deviation = float((intervals - typical_interval).abs().median())
    return median_absolute_deviation / typical_interval


def _classify_confidence(
    purchase_count: int,
    distinct_purchase_dates: int,
    interval_count: int,
    variability: float | None,
) -> str:
    if purchase_count <= 1 or distinct_purchase_dates <= 1 or interval_count == 0:
        return "Insuficiente"
    if purchase_count >= 4 and interval_count >= 3 and variability is not None:
        if variability <= 0.25:
            return "Alta"
    if purchase_count >= 3 and interval_count >= 2 and variability is not None:
        if variability <= 0.60:
            return "Media"
    return "Baja"


def _build_commercial_pattern(
    confidence: str,
    concentrated_purchases: bool,
) -> str:
    if concentrated_purchases:
        return "Compras concentradas"
    return {
        "Alta": "Ciclo consistente",
        "Media": "Ciclo razonable",
        "Baja": "Patrón irregular",
        "Insuficiente": "Historial insuficiente",
    }[confidence]


def _build_repurchase_category(
    is_overdue: bool,
    is_normal: bool,
    confidence: str,
    commercial_pattern: str,
) -> str:
    if is_overdue:
        return "Recompra esperada atrasada"
    if is_normal:
        return "Dentro de ciclo normal"
    if confidence == "Insuficiente":
        return "Historial insuficiente"
    if confidence in {"Alta", "Media"}:
        return "Confianza alta/media"
    return commercial_pattern


def _build_time_suggestion(commercial_pattern: str, is_overdue: bool) -> str:
    if commercial_pattern == "Compras concentradas":
        return (
            "Revisar manualmente; compras concentradas no permiten inferir "
            "ciclo estable."
        )
    if commercial_pattern == "Patrón irregular":
        return "Monitorear; no priorizar sólo por ciclo."
    if commercial_pattern == "Historial insuficiente":
        return "No inferir recompra; evaluar por venta o criterio comercial."
    if commercial_pattern == "Ciclo consistente" and is_overdue:
        return "Revisar recuperación comercial."
    if commercial_pattern == "Ciclo razonable" and is_overdue:
        return "Validar si corresponde contacto comercial."
    return "Monitorear próxima recompra según patrón histórico."


def _detected_column(
    detection: ColumnDetectionResult,
    key: str,
) -> str | None:
    field = detection.get(key)
    return field.detected_column if field else None


def _empty_result() -> CommercialTimeResult:
    return CommercialTimeResult(
        overdue_clients=0,
        normal_cycle_clients=0,
        reliable_clients=0,
        insufficient_history_clients=0,
        reference_date=None,
        clients=pd.DataFrame(),
    )
