from src.models import AnalysisCapabilities, AnalysisLevel, ColumnDetectionResult


def build_capabilities(
    level: AnalysisLevel,
    detection: ColumnDetectionResult,
) -> AnalysisCapabilities:
    available: list[str] = []
    unavailable: list[str] = []

    if level.level >= 1:
        available.append("Ventas acumuladas por cliente.")
        available.append("Ranking de clientes por monto de venta.")
    else:
        unavailable.append("Ventas por cliente: falta cliente y/o monto de venta.")

    if level.level >= 2:
        available.append("Ventas por periodo.")
        available.append("Evolucion de ventas por cliente en el tiempo.")
    else:
        unavailable.append("Analisis temporal: falta fecha.")

    if level.level >= 3:
        available.append("Ventas por producto o SKU.")
        available.append("Cantidad vendida y mix comercial.")
    else:
        missing_product = not (
            detection.has("producto_descripcion") or detection.has("sku_codigo")
        )
        missing_quantity = not detection.has("cantidad")
        reasons = []
        if missing_product:
            reasons.append("producto/SKU")
        if missing_quantity:
            reasons.append("cantidad")
        if reasons:
            unavailable.append("Analisis de producto: falta " + " y ".join(reasons) + ".")

    if level.level >= 4:
        available.append("Margen, costo o utilidad comercial.")
        available.append("Rentabilidad por cliente, producto y vendedor.")
    else:
        unavailable.append("Rentabilidad comercial: falta costo, margen o utilidad.")

    if detection.has("vendedor"):
        available.append("Ventas por vendedor.")
    else:
        unavailable.append("Analisis por vendedor: falta vendedor.")

    if detection.has("categoria_familia"):
        available.append("Ventas por categoria o familia.")
    else:
        unavailable.append("Analisis por categoria/familia: falta categoria o familia.")

    return AnalysisCapabilities(available=available, unavailable=unavailable)
