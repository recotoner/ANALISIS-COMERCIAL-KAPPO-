from src.models import AnalysisLevel, ColumnDetectionResult


def classify_analysis_level(detection: ColumnDetectionResult) -> AnalysisLevel:
    has_cliente = detection.has("cliente")
    has_monto = detection.has("monto_venta")
    has_fecha = detection.has("fecha")
    has_product = detection.has("producto_descripcion") or detection.has("sku_codigo")
    has_quantity = detection.has("cantidad")
    has_profitability = detection.has("costo") or detection.has("margen_utilidad")

    if not (has_cliente and has_monto):
        return AnalysisLevel(
            level=0,
            name="Nivel 0: data insuficiente",
            description=(
                "No se detectan las columnas minimas de cliente y monto de venta. "
                "Antes de construir informes hay que corregir o mapear la data."
            ),
        )

    if not has_fecha:
        return AnalysisLevel(
            level=1,
            name="Nivel 1: ventas por cliente",
            description="La data permite medir ventas acumuladas por cliente.",
        )

    if not (has_product and has_quantity):
        return AnalysisLevel(
            level=2,
            name="Nivel 2: ventas por cliente y periodo",
            description="La data permite analizar ventas por cliente y evolucion temporal.",
        )

    if not has_profitability:
        return AnalysisLevel(
            level=3,
            name="Nivel 3: ventas por cliente, producto y cantidad",
            description=(
                "La data permite analizar clientes, productos, volumen y mix vendido, "
                "pero no rentabilidad."
            ),
        )

    return AnalysisLevel(
        level=4,
        name="Nivel 4: rentabilidad comercial",
        description=(
            "La data permite analizar ventas por cliente, periodo, producto, cantidad "
            "y rentabilidad comercial."
        ),
    )
