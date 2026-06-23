from dataclasses import dataclass

import pandas as pd

from src.models import ColumnDetectionResult


@dataclass(frozen=True)
class ClientAnalysisResult:
    total_clients: int
    total_sales: float
    clients_for_50_percent: int
    clients_for_70_percent: int
    clients_for_80_percent: int
    top_1_concentration: float
    top_5_concentration: float
    top_10_concentration: float
    average_sales_per_client: float
    median_sales_per_client: float
    ranking: pd.DataFrame


def _detected_column(detection: ColumnDetectionResult, key: str) -> str | None:
    field = detection.get(key)
    return field.detected_column if field else None


def _minimum_clients_for_share(cumulative_share: pd.Series, threshold: float) -> int:
    if cumulative_share.empty:
        return 0

    reached_positions = cumulative_share.to_numpy().nonzero()[0]
    threshold_positions = (cumulative_share >= threshold).to_numpy().nonzero()[0]
    if len(threshold_positions):
        return int(threshold_positions[0]) + 1
    return len(reached_positions) or len(cumulative_share)


def build_client_analysis(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> ClientAnalysisResult:
    client_column = _detected_column(detection, "cliente")
    amount_column = _detected_column(detection, "monto_venta")
    date_column = _detected_column(detection, "fecha")

    if not client_column or not amount_column:
        return _empty_result()
    if client_column not in df.columns or amount_column not in df.columns:
        return _empty_result()

    working_df = df[[client_column, amount_column]].copy()
    working_df[client_column] = working_df[client_column].astype("string").str.strip()
    working_df[amount_column] = pd.to_numeric(working_df[amount_column], errors="coerce")
    valid_mask = (
        working_df[client_column].notna()
        & working_df[client_column].ne("")
        & working_df[amount_column].notna()
    )

    if date_column and date_column in df.columns:
        valid_mask &= pd.to_datetime(
            df[date_column],
            errors="coerce",
            dayfirst=True,
        ).notna()

    working_df = working_df.loc[valid_mask]
    if working_df.empty:
        return _empty_result()

    ranking = (
        working_df.groupby(client_column, as_index=False)[amount_column]
        .sum()
        .sort_values(amount_column, ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    ranking.columns = ["cliente", "venta_total"]

    total_sales = float(ranking["venta_total"].sum())
    if total_sales > 0:
        ranking["participacion"] = ranking["venta_total"] / total_sales
    else:
        ranking["participacion"] = 0.0
    ranking["participacion_acumulada"] = ranking["participacion"].cumsum()
    ranking.insert(0, "ranking", range(1, len(ranking) + 1))

    clients_50 = _minimum_clients_for_share(ranking["participacion_acumulada"], 0.50)
    clients_70 = _minimum_clients_for_share(ranking["participacion_acumulada"], 0.70)
    clients_80 = _minimum_clients_for_share(ranking["participacion_acumulada"], 0.80)
    median_sales = float(ranking["venta_total"].median())

    ranking["clasificacion_cliente"] = "Cliente de bajo volumen"
    ranking.loc[
        (ranking["ranking"] > clients_80)
        & (ranking["venta_total"] > median_sales),
        "clasificacion_cliente",
    ] = "Cliente relevante"
    ranking.loc[
        ranking["ranking"] <= clients_80,
        "clasificacion_cliente",
    ] = "Cliente estrategico"

    return ClientAnalysisResult(
        total_clients=len(ranking),
        total_sales=total_sales,
        clients_for_50_percent=clients_50,
        clients_for_70_percent=clients_70,
        clients_for_80_percent=clients_80,
        top_1_concentration=float(ranking["participacion"].head(1).sum()),
        top_5_concentration=float(ranking["participacion"].head(5).sum()),
        top_10_concentration=float(ranking["participacion"].head(10).sum()),
        average_sales_per_client=float(ranking["venta_total"].mean()),
        median_sales_per_client=median_sales,
        ranking=ranking,
    )


def _empty_result() -> ClientAnalysisResult:
    return ClientAnalysisResult(
        total_clients=0,
        total_sales=0.0,
        clients_for_50_percent=0,
        clients_for_70_percent=0,
        clients_for_80_percent=0,
        top_1_concentration=0.0,
        top_5_concentration=0.0,
        top_10_concentration=0.0,
        average_sales_per_client=0.0,
        median_sales_per_client=0.0,
        ranking=pd.DataFrame(
            columns=[
                "ranking",
                "cliente",
                "venta_total",
                "participacion",
                "participacion_acumulada",
                "clasificacion_cliente",
            ]
        ),
    )
