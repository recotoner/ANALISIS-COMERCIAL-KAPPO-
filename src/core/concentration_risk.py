from dataclasses import dataclass

import pandas as pd

from src.core.client_analysis import ClientAnalysisResult


@dataclass(frozen=True)
class ConcentrationRiskResult:
    risk_level: str
    impact_message: str
    executive_summary: str
    top_1_concentration: float
    top_3_concentration: float
    top_5_concentration: float
    top_10_concentration: float
    clients_for_50_percent: int
    clients_for_70_percent: int
    clients_for_80_percent: int
    principal_client: str | None
    principal_client_sales: float
    principal_client_share: float
    critical_clients: pd.DataFrame


def build_concentration_risk(
    client_analysis: ClientAnalysisResult,
) -> ConcentrationRiskResult:
    ranking = client_analysis.ranking
    top_3 = float(ranking["participacion"].head(3).sum()) if not ranking.empty else 0.0
    principal_client = None if ranking.empty else str(ranking.iloc[0]["cliente"])
    principal_sales = 0.0 if ranking.empty else float(ranking.iloc[0]["venta_total"])

    risk_level = _classify_risk(
        client_analysis.top_1_concentration,
        client_analysis.top_5_concentration,
        client_analysis.top_10_concentration,
    )
    impact_message = {
        "Bajo": "La venta se encuentra relativamente distribuida.",
        "Medio": "Existe concentracion relevante, pero no critica.",
        "Alto": (
            "La perdida o reduccion de compra de uno o mas clientes principales "
            "podria afectar significativamente la venta total."
        ),
    }[risk_level]

    risk_adjective = {"Bajo": "baja", "Medio": "media", "Alto": "alta"}[risk_level]
    top_5_label = f"{client_analysis.top_5_concentration:.1%}".replace(".", ",")
    top_10_label = f"{client_analysis.top_10_concentration:.1%}".replace(".", ",")
    executive_summary = (
        f"La cartera presenta una concentracion {risk_adjective}: los Top 5 "
        f"clientes explican {top_5_label} de la venta y los Top 10 explican "
        f"{top_10_label}. "
    )
    if risk_level == "Alto":
        executive_summary += (
            "Esto evidencia dependencia comercial relevante respecto de un grupo "
            "reducido de clientes."
        )
    elif risk_level == "Medio":
        executive_summary += "La dependencia debe monitorearse periodicamente."
    else:
        executive_summary += "La exposicion a pocos clientes es acotada."

    critical_clients = ranking.head(10).copy()
    if not critical_clients.empty:
        critical_clients["nivel_criticidad"] = "Relevante"
        critical_clients.loc[
            critical_clients["ranking"] <= client_analysis.clients_for_80_percent,
            "nivel_criticidad",
        ] = "Estrategico"
        critical_clients.loc[
            critical_clients["ranking"] <= client_analysis.clients_for_50_percent,
            "nivel_criticidad",
        ] = "Critico"

    return ConcentrationRiskResult(
        risk_level=risk_level,
        impact_message=impact_message,
        executive_summary=executive_summary,
        top_1_concentration=client_analysis.top_1_concentration,
        top_3_concentration=top_3,
        top_5_concentration=client_analysis.top_5_concentration,
        top_10_concentration=client_analysis.top_10_concentration,
        clients_for_50_percent=client_analysis.clients_for_50_percent,
        clients_for_70_percent=client_analysis.clients_for_70_percent,
        clients_for_80_percent=client_analysis.clients_for_80_percent,
        principal_client=principal_client,
        principal_client_sales=principal_sales,
        principal_client_share=client_analysis.top_1_concentration,
        critical_clients=critical_clients,
    )


def _classify_risk(top_1: float, top_5: float, top_10: float) -> str:
    if top_5 > 0.50 or top_10 > 0.65 or top_1 > 0.25:
        return "Alto"
    if 0.30 <= top_5 <= 0.50 or 0.45 <= top_10 <= 0.65:
        return "Medio"
    return "Bajo"
