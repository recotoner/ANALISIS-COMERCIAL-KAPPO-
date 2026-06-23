import re
import unicodedata
from collections.abc import Iterable

import pandas as pd

from src.models import ColumnDetectionResult, KeyColumnDetection


KEY_COLUMN_ALIASES: dict[str, tuple[str, list[str]]] = {
    "cliente": (
        "Cliente",
        [
            "cliente",
            "razon social",
            "razon_social",
            "nombre cliente",
            "nombre_cliente",
            "empresa",
            "cuenta",
        ],
    ),
    "rut_cliente": (
        "RUT cliente",
        [
            "rut",
            "rut cliente",
            "rut_cliente",
            "ruc",
            "identificacion",
            "tax id",
        ],
    ),
    "fecha": (
        "Fecha",
        [
            "fecha",
            "fecha emision",
            "fecha_emision",
            "fecha documento",
            "fecha_documento",
        ],
    ),
    "documento_folio": (
        "Documento o folio",
        [
            "folio",
            "documento",
            "numero documento",
            "n documento",
            "num documento",
            "factura",
            "boleta",
        ],
    ),
    "monto_venta": (
        "Monto venta",
        [
            "monto venta",
            "monto_venta",
            "total linea",
            "total_linea",
            "venta",
            "ventas",
            "neto",
            "total",
            "importe",
        ],
    ),
    "producto_descripcion": (
        "Producto o descripcion",
        [
            "producto",
            "descripcion",
            "descripcion producto",
            "glosa",
            "item",
            "articulo",
        ],
    ),
    "sku_codigo": (
        "SKU o codigo",
        [
            "sku",
            "codigo",
            "cod producto",
            "codigo producto",
            "codigo_producto",
            "referencia",
        ],
    ),
    "cantidad": (
        "Cantidad",
        [
            "cantidad",
            "cantidad equivalente",
            "cantidad_equivalente",
            "unidades",
            "qty",
        ],
    ),
    "precio_unitario": (
        "Precio unitario",
        [
            "precio un",
            "precio_un",
            "precio unitario",
            "precio_unitario",
            "precio unidad",
            "valor unitario",
        ],
    ),
    "vendedor": (
        "Vendedor",
        [
            "vendedor",
            "ejecutivo",
            "comercial",
            "asesor",
        ],
    ),
    "categoria_familia": (
        "Categoria o familia",
        [
            "categoria",
            "familia",
            "linea",
            "grupo producto",
            "grupo_producto",
            "unidad de negocio",
            "unidad_de_negocio",
        ],
    ),
    "costo": (
        "Costo",
        [
            "costo",
            "costo venta unitario",
            "costo_venta_unitario",
            "costo venta total",
            "costo_venta_total",
            "costo unitario",
            "costo total",
        ],
    ),
    "margen_utilidad": (
        "Margen o utilidad",
        [
            "margen",
            "utilidad",
            "margen contrib",
            "margen_contrib",
            "margen contrib $",
            "margen contrib %",
            "rentabilidad",
        ],
    ),
}


def normalize_column_name(name: object) -> str:
    text = "" if name is None else str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().strip()
    text = text.replace("%", " porcentaje ")
    text = re.sub(r"[$#./\\()]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    normalization_map = {str(column): normalize_column_name(column) for column in df.columns}
    normalized_df = df.rename(columns=normalization_map)
    return normalized_df, normalization_map


def _contains_alias(column: str, alias: str) -> bool:
    return (
        column.startswith(f"{alias}_")
        or column.endswith(f"_{alias}")
        or f"_{alias}_" in column
    )


def _find_best_column(
    normalized_columns: list[tuple[str, str]],
    aliases: Iterable[str],
) -> str | None:
    normalized_aliases = [normalize_column_name(alias) for alias in aliases]

    for alias in normalized_aliases:
        for normalized_column, original_column in normalized_columns:
            if normalized_column == alias:
                return original_column

    for alias in normalized_aliases:
        for normalized_column, original_column in normalized_columns:
            if _contains_alias(normalized_column, alias):
                return original_column

    return None


def detect_key_columns(columns: Iterable[object]) -> ColumnDetectionResult:
    original_columns = [str(column) for column in columns]
    normalized_columns = [
        (normalize_column_name(column), str(column))
        for column in original_columns
    ]

    fields: list[KeyColumnDetection] = []

    for key, (label, aliases) in KEY_COLUMN_ALIASES.items():
        detected_column = _find_best_column(normalized_columns, aliases)

        fields.append(
            KeyColumnDetection(
                key=key,
                label=label,
                aliases=aliases,
                detected_column=detected_column,
            )
        )

    return ColumnDetectionResult(fields=fields)
