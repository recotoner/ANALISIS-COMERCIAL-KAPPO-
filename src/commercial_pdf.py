from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


KAPPO_NAVY = colors.HexColor("#082D5F")
KAPPO_SOFT = colors.HexColor("#EAF4FC")
KAPPO_LINE = colors.HexColor("#D8E2EC")
KAPPO_TEXT = colors.HexColor("#14233A")


def build_executive_clients_pdf(
    *,
    summary: dict[str, Any],
    ranking: pd.DataFrame,
    agenda: pd.DataFrame,
    commercial_time_clients: pd.DataFrame,
    logo_path: str | Path | None = None,
) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.35 * cm,
        leftMargin=1.35 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.15 * cm,
        title="Análisis Ejecutivo de Clientes",
    )
    styles = _build_styles()
    story: list[Any] = []

    _add_cover(story, styles, summary, logo_path)
    story.append(PageBreak())
    _add_executive_summary(story, styles, summary)
    _add_main_indicators(story, styles, summary)
    _add_commercial_concentration(story, styles, summary, ranking, agenda)
    story.append(PageBreak())
    _add_prioritization_guide(story, styles, summary, agenda)
    _add_repurchase_intelligence(story, styles, summary, commercial_time_clients)
    _add_opportunities_and_monitoring(story, styles, agenda, commercial_time_clients)
    _add_deliverables(story, styles)
    _add_methodology_and_close(story, styles)

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output.getvalue()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KappoTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=31,
            textColor=KAPPO_NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "KappoSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=KAPPO_TEXT,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "KappoSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=KAPPO_NAVY,
            spaceBefore=12,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "KappoBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=KAPPO_TEXT,
            spaceAfter=6,
        ),
        "note": ParagraphStyle(
            "KappoNote",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=KAPPO_TEXT,
            backColor=KAPPO_SOFT,
            borderColor=KAPPO_LINE,
            borderWidth=0.5,
            borderPadding=7,
            spaceBefore=5,
            spaceAfter=8,
        ),
    }


def _add_cover(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
    logo_path: str | Path | None,
) -> None:
    story.append(Spacer(1, 2.1 * cm))
    logo = _safe_logo(logo_path)
    if logo is not None:
        story.append(logo)
        story.append(Spacer(1, 1 * cm))
    else:
        story.append(Paragraph("Kappo Consultores", styles["title"]))
    story.append(Paragraph("Análisis Ejecutivo de Clientes", styles["title"]))
    story.append(
        Paragraph("Diagnóstico comercial basado en informe de ventas", styles["subtitle"])
    )
    story.append(Spacer(1, 1 * cm))
    cover_data = [
        ["Período analizado", str(summary.get("period_label", "No determinado"))],
        ["Fecha de emisión", str(summary.get("emission_date", ""))],
    ]
    story.append(_table(cover_data, [5.2 * cm, 9.2 * cm], small=False, header=False))


def _add_executive_summary(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
) -> None:
    story.append(Paragraph("Resumen ejecutivo", styles["section"]))
    conclusion = (
        "El informe permite una lectura ejecutiva de clientes con foco en "
        f"concentración, evolución comercial y recompra esperada. La data fue "
        f"clasificada en {summary.get('level_label', 'Nivel no determinado')} "
        f"con calidad general {summary.get('general_quality', 'no determinada')}. "
        f"La venta total analizada alcanza {_money(summary.get('total_sales'))} "
        f"en {summary.get('total_clients', 0)} clientes. "
        f"El Top 10 concentra {_percent(summary.get('top_10_concentration'))} "
        f"de la venta, con riesgo de concentración "
        f"{summary.get('risk_level', 'no determinado').lower()}."
    )
    story.append(Paragraph(conclusion, styles["body"]))
    story.append(
        Paragraph(
            "Las alertas y sugerencias deben entenderse como una guía de revisión "
            "comercial basada en ventas; antes de ejecutar acciones, corresponde "
            "validar el estado operativo del cliente en CRM.",
            styles["note"],
        )
    )


def _add_main_indicators(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
) -> None:
    story.append(Paragraph("Indicadores principales", styles["section"]))
    rows = [
        ["Venta total", _money(summary.get("total_sales")), "Clientes únicos", _number(summary.get("total_clients"))],
        ["Concentración Top 5", _percent(summary.get("top_5_concentration")), "Concentración Top 10", _percent(summary.get("top_10_concentration"))],
        ["Clientes que explican 80%", _number(summary.get("clients_for_80_percent")), "Riesgo de concentración", summary.get("risk_level", "N/D")],
        ["Alertas críticas", _number(summary.get("critical_alerts")), "Alertas relevantes", _number(summary.get("relevant_alerts"))],
        ["Oportunidades", _number(summary.get("opportunities")), "Clientes inactivos", _number(summary.get("inactive_clients"))],
    ]
    story.append(_table(rows, [4.1 * cm, 3.2 * cm, 4.1 * cm, 3.2 * cm], small=False, header=False))


def _add_commercial_concentration(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
    ranking: pd.DataFrame,
    agenda: pd.DataFrame,
) -> None:
    story.append(Paragraph("Concentración comercial", styles["section"]))
    story.append(
        Paragraph(
            "La concentración comercial resume qué tan dependiente está la venta "
            "de los principales clientes. Un mayor peso del Top 5 o Top 10 aumenta "
            "la sensibilidad ante caídas de compra o pérdida de cuentas relevantes.",
            styles["body"],
        )
    )
    merged = ranking.copy()
    if not agenda.empty:
        extras = _unique_client_columns(
            agenda,
            ["cliente", "vendedor_responsable_sugerido", "alerta_comercial"],
        )
        merged = merged.merge(extras, on="cliente", how="left")
    rows = [["Cliente", "Venta total", "Part. %", "Vendedor", "Alerta"]]
    for _, row in merged.head(10).iterrows():
        rows.append(
            [
                row.get("cliente", ""),
                _money(row.get("venta_total")),
                _percent(row.get("participacion")),
                row.get("vendedor_responsable_sugerido", "Sin vendedor identificado"),
                row.get("alerta_comercial", "Sin alerta"),
            ]
        )
    story.append(_table(rows, [5.3 * cm, 2.6 * cm, 1.8 * cm, 3 * cm, 2.7 * cm]))


def _add_prioritization_guide(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
    agenda: pd.DataFrame,
) -> None:
    story.append(Paragraph("Guía de priorización comercial", styles["section"]))
    rows = [
        ["Revisión prioritaria", _number(summary.get("high_priority_actions"))],
        ["Seguimiento sugerido", _number(summary.get("medium_priority_actions"))],
        ["Monitoreo", _number(summary.get("low_priority_actions"))],
    ]
    story.append(_table(rows, [7 * cm, 3 * cm], small=False, header=False))
    table_rows = [
        [
            "Cliente",
            "Vendedor",
            "Venta",
            "Part. %",
            "Prioridad",
            "Tipo",
            "Alerta",
            "Motivo",
            "Validación CRM",
        ]
    ]
    for _, row in agenda.head(12).iterrows():
        table_rows.append(
            [
                row.get("cliente", ""),
                row.get("vendedor_responsable_sugerido", "Sin vendedor identificado"),
                _money(row.get("venta_total")),
                _percent(row.get("participacion")),
                row.get("prioridad_gestion", ""),
                row.get("tipo_sugerencia", ""),
                row.get("alerta_comercial", ""),
                row.get("motivo_comercial", row.get("por_que_importa", "")),
                row.get("validacion_requerida_crm", ""),
            ]
        )
    story.append(_table(table_rows, [3.1 * cm, 2 * cm, 1.8 * cm, 1.2 * cm, 1.5 * cm, 2.2 * cm, 1.8 * cm, 3.1 * cm, 3.2 * cm]))


def _add_repurchase_intelligence(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    summary: dict[str, Any],
    commercial_time_clients: pd.DataFrame,
) -> None:
    story.append(Paragraph("Inteligencia de tiempo comercial", styles["section"]))
    story.append(
        Paragraph(
            "La recompra esperada se calcula considerando meses calendario con "
            "compra, no documentos individuales dentro del mismo mes. Es una "
            "referencia de gestión comercial y no una predicción exacta.",
            styles["note"],
        )
    )
    rows = [
        ["Recompra esperada atrasada", _number(summary.get("overdue_clients")), "Dentro de ciclo normal", _number(summary.get("normal_cycle_clients"))],
        ["Confianza alta/media", _number(summary.get("reliable_clients")), "Historial insuficiente", _number(summary.get("insufficient_history_clients"))],
    ]
    story.append(_table(rows, [4.8 * cm, 2.5 * cm, 4.8 * cm, 2.5 * cm], small=False, header=False))
    if commercial_time_clients.empty:
        return
    time_data = commercial_time_clients.copy()
    time_data["_priority_time"] = (
        time_data["categoria_recompra"].eq("Recompra esperada atrasada").astype(int)
    )
    time_data["_reliable"] = time_data["lectura_comercial_patron"].isin(
        ["Ciclo consistente", "Ciclo razonable"]
    ).astype(int)
    time_data = time_data.sort_values(
        ["_priority_time", "_reliable", "venta_total", "dias_atraso"],
        ascending=[False, False, False, False],
        kind="stable",
    ).head(10)
    table_rows = [
        [
            "Cliente",
            "Vendedor",
            "Categoría",
            "Lectura",
            "Sugerencia",
            "Última compra",
            "Próxima",
            "Atraso",
            "Confianza",
        ]
    ]
    for _, row in time_data.iterrows():
        table_rows.append(
            [
                row.get("cliente", ""),
                row.get("vendedor_responsable_sugerido", "Sin vendedor identificado"),
                row.get("categoria_recompra", ""),
                row.get("lectura_comercial_patron", ""),
                row.get("sugerencia_por_tiempo", ""),
                _date(row.get("ultima_compra")),
                _date(row.get("proxima_compra_esperada")),
                _number(row.get("dias_atraso")),
                row.get("confianza_recompra", ""),
            ]
        )
    story.append(_table(table_rows, [3 * cm, 1.9 * cm, 2.5 * cm, 2.3 * cm, 3.2 * cm, 1.7 * cm, 1.7 * cm, 1.1 * cm, 1.5 * cm]))


def _add_opportunities_and_monitoring(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
    agenda: pd.DataFrame,
    commercial_time_clients: pd.DataFrame,
) -> None:
    story.append(Paragraph("Oportunidades y clientes a monitorear", styles["section"]))
    opportunities = agenda[
        agenda.get("alerta_comercial", pd.Series(dtype=str)).eq("Oportunidad")
    ].head(8)
    if not opportunities.empty:
        rows = [["Cliente", "Vendedor", "Venta", "Tendencia", "Sugerencia"]]
        for _, row in opportunities.iterrows():
            rows.append(
                [
                    row.get("cliente", ""),
                    row.get("vendedor_responsable_sugerido", ""),
                    _money(row.get("venta_total")),
                    row.get("tendencia", ""),
                    row.get("tipo_sugerencia", ""),
                ]
            )
        story.append(_table(rows, [4.3 * cm, 2.6 * cm, 2.3 * cm, 2.3 * cm, 4 * cm]))
    manual_review = commercial_time_clients[
        commercial_time_clients.get("categoria_recompra", pd.Series(dtype=str)).isin(
            ["Compras concentradas", "Historial insuficiente", "Patrón irregular", "Patron irregular"]
        )
    ].sort_values("venta_total", ascending=False, kind="stable").head(8)
    if not manual_review.empty:
        story.append(
            Paragraph(
                "Clientes con compras concentradas, historial insuficiente o patrón "
                "irregular deben revisarse manualmente y no tratarse como alertas "
                "fuertes solo por tiempo.",
                styles["body"],
            )
        )
        rows = [["Cliente", "Categoría", "Lectura", "Venta total", "Confianza"]]
        for _, row in manual_review.iterrows():
            rows.append(
                [
                    row.get("cliente", ""),
                    row.get("categoria_recompra", ""),
                    row.get("lectura_comercial_patron", ""),
                    _money(row.get("venta_total")),
                    row.get("confianza_recompra", ""),
                ]
            )
        story.append(_table(rows, [4.6 * cm, 3.1 * cm, 3.1 * cm, 2.4 * cm, 2 * cm]))


def _add_deliverables(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(Paragraph("Entregables del análisis", styles["section"]))
    story.append(
        Paragraph(
            "Este diagnóstico se entrega en dos formatos complementarios: un PDF "
            "ejecutivo para lectura gerencial y un Excel operativo para revisión, "
            "filtros y gestión comercial detallada. El PDF resume los principales "
            "hallazgos y recomendaciones; el Excel contiene la base accionable "
            "para priorización, seguimiento y validación comercial.",
            styles["note"],
        )
    )


def _add_methodology_and_close(
    story: list[Any],
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(Paragraph("Metodología y alcance", styles["section"]))
    story.append(
        Paragraph(
            "El análisis se basa en el informe de ventas cargado. Las "
            "recomendaciones deben validarse contra CRM antes de ejecutar "
            "acciones. La app no reemplaza el CRM ni la gestión comercial. La "
            "recompra esperada es una señal de gestión, no una predicción exacta. "
            "Clientes con historial insuficiente, compras concentradas o patrón "
            "irregular no deben tratarse como alertas fuertes solo por tiempo.",
            styles["body"],
        )
    )
    story.append(Paragraph("Cierre Kappo", styles["section"]))
    story.append(
        Paragraph(
            "Este análisis permite priorizar la revisión comercial de clientes en "
            "función de concentración, evolución reciente, señales de inactividad, "
            "oportunidades e inteligencia de recompra. La gestión final debe ser "
            "validada por el equipo comercial y contrastada con el CRM o registro "
            "operativo disponible.",
            styles["note"],
        )
    )


def _table(
    rows: list[list[Any]],
    widths: list[float],
    small: bool = True,
    header: bool = True,
) -> Table:
    body_style = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=6.5 if small else 8.5,
        leading=8 if small else 11,
        textColor=KAPPO_TEXT,
    )
    header_style = ParagraphStyle(
        "TableHeaderCell",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    wrapped = [
        [
            Paragraph(_escape_cell(value), header_style if header and row_index == 0 else body_style)
            for value in row
        ]
        for row_index, row in enumerate(rows)
    ]
    table = Table(wrapped, colWidths=widths, repeatRows=1 if header and len(rows) > 1 else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.35, KAPPO_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header and len(rows) > 1:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), KAPPO_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, KAPPO_SOFT]),
            ]
        )
    else:
        style.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, KAPPO_SOFT]))
    table.setStyle(TableStyle(style))
    return KeepTogether([table, Spacer(1, 0.18 * cm)])


def _safe_logo(logo_path: str | Path | None) -> Image | None:
    if not logo_path:
        return None
    path = Path(logo_path)
    if not path.exists():
        return None
    image = Image(str(path), width=6.2 * cm, height=1.95 * cm)
    image.hAlign = "CENTER"
    return image


def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(KAPPO_LINE)
    canvas.line(doc.leftMargin, 0.85 * cm, A4[0] - doc.rightMargin, 0.85 * cm)
    canvas.setFillColor(KAPPO_NAVY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(doc.leftMargin, 0.48 * cm, "Kappo Consultores - Análisis Ejecutivo de Clientes")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.48 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _unique_client_columns(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in data.columns]
    if "cliente" not in available:
        return pd.DataFrame(columns=["cliente"])
    return data[available].drop_duplicates(subset=["cliente"], keep="first")


def _escape_cell(value: Any) -> str:
    text = "" if pd.isna(value) else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _money(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "N/D"
    return "$" + f"{number:,.0f}".replace(",", ".")


def _percent(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "N/D"
    return f"{number:.1%}".replace(".", ",")


def _number(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "N/D"
    return f"{number:,.0f}".replace(",", ".")


def _date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "No determinada"
    return pd.Timestamp(value).strftime("%d/%m/%Y")


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
