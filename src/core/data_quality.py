import pandas as pd

from src.models import (
    ColumnDetectionResult,
    DocumentQualityMetrics,
    ProfitabilityCoverageMetrics,
    SkuCoverageMetrics,
)


def _missing_ratio(series: pd.Series) -> float:
    if len(series) == 0:
        return 1.0
    return float(series.isna().mean())


def _detected_column(detection: ColumnDetectionResult, key: str) -> str | None:
    field = detection.get(key)
    return field.detected_column if field else None


def _valid_text_mask(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip().str.lower()
    invalid_values = {"", "nan", "none", "null", "no aplica", "(no aplica)", "n/a"}
    return series.notna() & ~cleaned.isin(invalid_values)


def _numeric_series(df: pd.DataFrame, column: str | None) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    return pd.to_numeric(df[column], errors="coerce")


def _valid_numeric_mask(df: pd.DataFrame, column: str | None) -> pd.Series:
    return _numeric_series(df, column).notna()


def _profitability_mask(df: pd.DataFrame, detection: ColumnDetectionResult) -> pd.Series:
    cost_column = _detected_column(detection, "costo")
    margin_column = _detected_column(detection, "margen_utilidad")
    cost_values = _numeric_series(df, cost_column)
    valid_cost_mask = cost_values.notna() & cost_values.ne(0)
    return valid_cost_mask | _valid_numeric_mask(df, margin_column)


def _safe_sum(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def build_document_quality_metrics(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> DocumentQualityMetrics:
    document_column = _detected_column(detection, "documento_folio")
    if not document_column or document_column not in df.columns:
        return DocumentQualityMetrics(
            total_unique_documents=0,
            multiline_documents=0,
            possible_exact_duplicates=0,
            possible_exact_duplicate_rows=0,
            document_column=None,
            comparison_columns=[],
        )

    multiline_candidate_keys = [
        "sku_codigo",
        "producto_descripcion",
        "cantidad",
        "monto_venta",
        "precio_unitario",
    ]
    comparison_columns = [
        column
        for column in (_detected_column(detection, key) for key in multiline_candidate_keys)
        if column and column in df.columns
    ]

    total_unique_documents = int(df[document_column].dropna().nunique())

    if not comparison_columns:
        return DocumentQualityMetrics(
            total_unique_documents=total_unique_documents,
            multiline_documents=0,
            possible_exact_duplicates=0,
            possible_exact_duplicate_rows=0,
            document_column=document_column,
            comparison_columns=[],
        )

    working_df = df[[document_column, *comparison_columns]].dropna(
        subset=[document_column]
    )
    repeated_documents = working_df[document_column][
        working_df[document_column].duplicated(keep=False)
    ]
    repeated_df = working_df[working_df[document_column].isin(repeated_documents)]

    multiline_documents = 0
    if not repeated_df.empty:
        combinations_by_document = repeated_df.groupby(document_column, dropna=False)[
            comparison_columns
        ].nunique(dropna=False)
        multiline_documents = int((combinations_by_document.gt(1).any(axis=1)).sum())

    exact_working_df = working_df.copy()
    exact_keys = [
        _detected_column(detection, "sku_codigo"),
        _detected_column(detection, "producto_descripcion"),
        _detected_column(detection, "cantidad"),
        _detected_column(detection, "monto_venta"),
        _detected_column(detection, "precio_unitario"),
    ]
    exact_columns = [
        column
        for column in exact_keys
        if column and column in exact_working_df.columns and column != document_column
    ]

    exact_subset = [document_column, *exact_columns]
    duplicate_mask = exact_working_df.duplicated(subset=exact_subset, keep=False)
    possible_exact_duplicate_rows = int(duplicate_mask.sum())
    possible_exact_duplicates = 0
    if possible_exact_duplicate_rows > 0:
        possible_exact_duplicates = int(
            exact_working_df.loc[duplicate_mask, exact_subset]
            .drop_duplicates()
            .shape[0]
        )

    return DocumentQualityMetrics(
        total_unique_documents=total_unique_documents,
        multiline_documents=multiline_documents,
        possible_exact_duplicates=possible_exact_duplicates,
        possible_exact_duplicate_rows=possible_exact_duplicate_rows,
        document_column=document_column,
        comparison_columns=comparison_columns,
    )


def build_sku_coverage_metrics(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> SkuCoverageMetrics:
    sku_column = _detected_column(detection, "sku_codigo")
    amount_column = _detected_column(detection, "monto_venta")
    margin_column = _detected_column(detection, "margen_utilidad")

    if sku_column and sku_column in df.columns:
        valid_sku_mask = _valid_text_mask(df[sku_column])
    else:
        valid_sku_mask = pd.Series(False, index=df.index)

    empty_sku_mask = ~valid_sku_mask
    amount_values = _numeric_series(df, amount_column)
    valid_amount_mask = amount_values.notna()

    valid_sku_sales = _safe_sum(amount_values[valid_sku_mask & valid_amount_mask])
    empty_sku_sales = _safe_sum(amount_values[empty_sku_mask & valid_amount_mask])
    total_sales_abs = abs(valid_sku_sales) + abs(empty_sku_sales)
    valid_sales_percentage = (
        abs(valid_sku_sales) / total_sales_abs if total_sales_abs else 0.0
    )
    empty_sales_percentage = (
        abs(empty_sku_sales) / total_sales_abs if total_sales_abs else 0.0
    )

    profitability_mask = _profitability_mask(df, detection)
    empty_sku_profitability_mask = empty_sku_mask & profitability_mask
    margin_values = _numeric_series(df, margin_column)
    empty_sku_profitability_amount = None
    if margin_column and margin_column in df.columns:
        empty_sku_profitability_amount = _safe_sum(
            margin_values[empty_sku_profitability_mask]
        )

    total_rows = len(df)
    valid_sku_rows = int(valid_sku_mask.sum())
    empty_sku_rows = int(empty_sku_mask.sum())

    return SkuCoverageMetrics(
        total_rows=total_rows,
        valid_sku_rows=valid_sku_rows,
        empty_sku_rows=empty_sku_rows,
        valid_sku_row_percentage=valid_sku_rows / total_rows if total_rows else 0.0,
        valid_sku_sales=valid_sku_sales,
        empty_sku_sales=empty_sku_sales,
        valid_sku_sales_percentage=valid_sales_percentage,
        empty_sku_sales_percentage=empty_sales_percentage,
        empty_sku_with_profitability_rows=int(empty_sku_profitability_mask.sum()),
        empty_sku_with_profitability_sales=_safe_sum(
            amount_values[empty_sku_profitability_mask & valid_amount_mask]
        ),
        empty_sku_profitability_amount=empty_sku_profitability_amount,
        sku_column=sku_column if sku_column in df.columns else None,
        amount_column=amount_column if amount_column in df.columns else None,
        profitability_column=margin_column if margin_column in df.columns else None,
    )


def build_profitability_coverage_metrics(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> ProfitabilityCoverageMetrics:
    amount_column = _detected_column(detection, "monto_venta")
    cost_column = _detected_column(detection, "costo")
    margin_column = _detected_column(detection, "margen_utilidad")

    amount_values = _numeric_series(df, amount_column)
    cost_values = _numeric_series(df, cost_column)
    margin_values = _numeric_series(df, margin_column)

    valid_amount_mask = amount_values.notna()
    valid_cost_mask = cost_values.notna() & cost_values.ne(0)
    valid_margin_mask = margin_values.notna()
    profitability_mask = valid_amount_mask & (valid_cost_mask | valid_margin_mask)

    total_sales = _safe_sum(amount_values[valid_amount_mask])
    sales_with_valid_cost = _safe_sum(amount_values[valid_cost_mask & valid_amount_mask])
    sales_without_valid_cost = _safe_sum(
        amount_values[(~valid_cost_mask) & valid_amount_mask]
    )
    total_sales_abs = abs(sales_with_valid_cost) + abs(sales_without_valid_cost)
    valid_cost_sales_percentage = (
        abs(sales_with_valid_cost) / total_sales_abs if total_sales_abs else 0.0
    )
    without_valid_cost_sales_percentage = (
        abs(sales_without_valid_cost) / total_sales_abs if total_sales_abs else 0.0
    )

    total_margin_amount = None
    if margin_column and margin_column in df.columns:
        total_margin_amount = _safe_sum(margin_values[valid_margin_mask])

    calculated_commercial_margin = None
    if total_sales:
        if total_margin_amount is not None:
            calculated_commercial_margin = total_margin_amount / total_sales
        elif cost_column and cost_column in df.columns:
            calculated_commercial_margin = (
                total_sales - _safe_sum(cost_values[valid_cost_mask])
            ) / total_sales

    profitability_rows = int(profitability_mask.sum())
    row_coverage = profitability_rows / len(df) if len(df) else 0.0
    if row_coverage >= 0.9 and valid_cost_sales_percentage >= 0.9:
        coverage_level = "alta"
    elif row_coverage >= 0.6 or valid_cost_sales_percentage >= 0.6:
        coverage_level = "parcial"
    else:
        coverage_level = "baja"

    return ProfitabilityCoverageMetrics(
        total_rows=len(df),
        valid_sales_amount_rows=int(valid_amount_mask.sum()),
        valid_cost_rows=int(valid_cost_mask.sum()),
        valid_margin_rows=int(valid_margin_mask.sum()),
        zero_cost_rows=int((cost_values.notna() & cost_values.eq(0)).sum()),
        null_cost_rows=int(cost_values.isna().sum()),
        null_margin_rows=int(margin_values.isna().sum()),
        negative_margin_rows=int((margin_values.notna() & margin_values.lt(0)).sum()),
        total_sales=total_sales,
        sales_with_valid_cost=sales_with_valid_cost,
        sales_without_valid_cost=sales_without_valid_cost,
        valid_cost_sales_percentage=valid_cost_sales_percentage,
        without_valid_cost_sales_percentage=without_valid_cost_sales_percentage,
        total_margin_amount=total_margin_amount,
        calculated_commercial_margin=calculated_commercial_margin,
        profitability_coverage_level=coverage_level,
        cost_column=cost_column if cost_column in df.columns else None,
        margin_column=margin_column if margin_column in df.columns else None,
        amount_column=amount_column if amount_column in df.columns else None,
    )


def build_analysis_datasets(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> dict[str, pd.DataFrame]:
    sku_column = _detected_column(detection, "sku_codigo")
    client_column = _detected_column(detection, "cliente")
    amount_column = _detected_column(detection, "monto_venta")

    if sku_column and sku_column in df.columns:
        valid_sku_mask = _valid_text_mask(df[sku_column])
    else:
        valid_sku_mask = pd.Series(False, index=df.index)

    client_mask = pd.Series(True, index=df.index)
    if client_column and client_column in df.columns:
        client_mask &= _valid_text_mask(df[client_column])
    if amount_column and amount_column in df.columns:
        client_mask &= _valid_numeric_mask(df, amount_column)

    product_column = _detected_column(detection, "producto_descripcion")
    product_mask = pd.Series(True, index=df.index)
    if product_column and product_column in df.columns:
        product_mask &= _valid_text_mask(df[product_column])

    amount_mask = _valid_numeric_mask(df, amount_column)
    profitability_mask = amount_mask & _profitability_mask(df, detection)

    return {
        "dataset_base": df.copy(),
        "dataset_cliente": df.loc[client_mask].copy(),
        "dataset_producto_sku": df.loc[valid_sku_mask].copy(),
        "dataset_rentabilidad_cliente": df.loc[client_mask & profitability_mask].copy(),
        "dataset_rentabilidad_producto_sku": df.loc[
            valid_sku_mask & product_mask & profitability_mask
        ].copy(),
        "dataset_sin_costo": df.loc[amount_mask & ~profitability_mask].copy(),
    }


def build_empty_sku_examples(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
    limit: int = 50,
) -> pd.DataFrame:
    sku_column = _detected_column(detection, "sku_codigo")
    if not sku_column or sku_column not in df.columns:
        return pd.DataFrame()

    empty_sku_df = df.loc[~_valid_text_mask(df[sku_column])].copy()
    if empty_sku_df.empty:
        return pd.DataFrame()

    document_type_column = "Documento" if "Documento" in empty_sku_df.columns else None
    folio_column = "Folio" if "Folio" in empty_sku_df.columns else None

    display_mapping = {
        "Documento": document_type_column,
        "Folio": folio_column or _detected_column(detection, "documento_folio"),
        "Cliente": _detected_column(detection, "cliente"),
        "Fecha": _detected_column(detection, "fecha"),
        "Producto/descripcion": _detected_column(detection, "producto_descripcion"),
        "Cantidad": _detected_column(detection, "cantidad"),
        "Monto linea": _detected_column(detection, "monto_venta"),
        "Costo": _detected_column(detection, "costo"),
        "Margen/utilidad": _detected_column(detection, "margen_utilidad"),
        "Vendedor": _detected_column(detection, "vendedor"),
    }
    display_columns = {
        label: column
        for label, column in display_mapping.items()
        if column and column in empty_sku_df.columns
    }

    return (
        empty_sku_df[list(display_columns.values())]
        .rename(columns={column: label for label, column in display_columns.items()})
        .head(limit)
    )


def build_missing_profitability_examples(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
    limit: int = 50,
) -> pd.DataFrame:
    amount_column = _detected_column(detection, "monto_venta")
    amount_mask = _valid_numeric_mask(df, amount_column)
    missing_profitability_df = df.loc[amount_mask & ~_profitability_mask(df, detection)].copy()
    if missing_profitability_df.empty:
        return pd.DataFrame()

    document_type_column = "Documento" if "Documento" in missing_profitability_df.columns else None
    folio_column = "Folio" if "Folio" in missing_profitability_df.columns else None
    display_mapping = {
        "Documento": document_type_column,
        "Folio": folio_column or _detected_column(detection, "documento_folio"),
        "Cliente": _detected_column(detection, "cliente"),
        "Fecha": _detected_column(detection, "fecha"),
        "SKU": _detected_column(detection, "sku_codigo"),
        "Producto": _detected_column(detection, "producto_descripcion"),
        "Cantidad": _detected_column(detection, "cantidad"),
        "Monto linea": amount_column,
        "Costo": _detected_column(detection, "costo"),
        "Margen/utilidad": _detected_column(detection, "margen_utilidad"),
        "Vendedor": _detected_column(detection, "vendedor"),
    }
    display_columns = {
        label: column
        for label, column in display_mapping.items()
        if column and column in missing_profitability_df.columns
    }

    return (
        missing_profitability_df[list(display_columns.values())]
        .rename(columns={column: label for label, column in display_columns.items()})
        .head(limit)
    )


def build_possible_exact_duplicate_examples(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
    limit: int = 50,
) -> pd.DataFrame:
    document_column = _detected_column(detection, "documento_folio")
    if not document_column or document_column not in df.columns:
        return pd.DataFrame()

    sku_column = _detected_column(detection, "sku_codigo")
    product_column = _detected_column(detection, "producto_descripcion")
    quantity_column = _detected_column(detection, "cantidad")
    amount_column = _detected_column(detection, "monto_venta")
    unit_price_column = _detected_column(detection, "precio_unitario")

    exact_df = df.copy()
    exact_columns = [
        column
        for column in [
            document_column,
            sku_column,
            product_column,
            quantity_column,
            amount_column,
            unit_price_column,
        ]
        if column and column in exact_df.columns
    ]

    if len(exact_columns) <= 1:
        return pd.DataFrame()

    duplicate_mask = exact_df.duplicated(subset=exact_columns, keep=False)
    duplicate_df = df.loc[duplicate_mask].copy()
    if duplicate_df.empty:
        return pd.DataFrame()

    display_mapping = {
        "documento": document_column,
        "cliente": _detected_column(detection, "cliente"),
        "fecha": _detected_column(detection, "fecha"),
        "SKU": sku_column,
        "producto": product_column,
        "cantidad": quantity_column,
        "monto linea": amount_column,
        "precio unitario": unit_price_column,
    }
    display_columns = {
        label: column
        for label, column in display_mapping.items()
        if column and column in duplicate_df.columns
    }

    return (
        duplicate_df[list(display_columns.values())]
        .rename(columns={column: label for label, column in display_columns.items()})
        .head(limit)
    )


def build_quality_warnings(
    df: pd.DataFrame,
    detection: ColumnDetectionResult,
) -> list[str]:
    warnings: list[str] = []

    if df.empty:
        return ["La hoja no contiene filas de datos."]

    if df.duplicated().any():
        duplicated_count = int(df.duplicated().sum())
        warnings.append(f"Existen {duplicated_count} filas completamente duplicadas.")

    for field in detection.found_fields:
        column = field.detected_column
        if not column or column not in df.columns:
            continue

        missing_ratio = _missing_ratio(df[column])
        if missing_ratio >= 0.5:
            warnings.append(
                f"La columna '{column}' tiene {missing_ratio:.0%} de valores vacios."
            )

    date_field = detection.get("fecha")
    if date_field and date_field.detected_column in df.columns:
        parsed_dates = pd.to_datetime(
            df[date_field.detected_column],
            errors="coerce",
            dayfirst=True,
        )
        invalid_ratio = float(parsed_dates.isna().mean())
        if invalid_ratio >= 0.2:
            warnings.append(
                f"La columna de fecha '{date_field.detected_column}' tiene "
                f"{invalid_ratio:.0%} de valores no interpretables como fecha."
            )

    for numeric_key in ["monto_venta", "cantidad", "precio_unitario", "costo", "margen_utilidad"]:
        field = detection.get(numeric_key)
        if not field or field.detected_column not in df.columns:
            continue

        numeric_values = pd.to_numeric(df[field.detected_column], errors="coerce")
        invalid_ratio = float(numeric_values.isna().mean())
        if invalid_ratio >= 0.2:
            warnings.append(
                f"La columna '{field.detected_column}' tiene {invalid_ratio:.0%} "
                "de valores no numericos."
            )

    missing_core = [
        field.label
        for field in detection.missing_fields
        if field.key in {"cliente", "fecha", "monto_venta"}
    ]
    if missing_core:
        warnings.append(
            "Faltan columnas base para un analisis comercial confiable: "
            + ", ".join(missing_core)
            + "."
        )

    return warnings
