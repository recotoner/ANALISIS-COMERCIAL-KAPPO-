import unittest

import pandas as pd

from src.core.column_detector import detect_key_columns
from src.core.data_quality import (
    build_analysis_datasets,
    build_document_quality_metrics,
    build_empty_sku_examples,
    build_missing_profitability_examples,
    build_possible_exact_duplicate_examples,
    build_profitability_coverage_metrics,
    build_quality_warnings,
    build_sku_coverage_metrics,
)


class DataQualityTests(unittest.TestCase):
    def test_separates_multiline_documents_from_exact_duplicates(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "SKU": "A",
                    "Producto": "Toner A",
                    "Cantidad": 1,
                    "Total Linea": 1000,
                    "Precio Un.": 1000,
                },
                {
                    "Folio": 100,
                    "SKU": "B",
                    "Producto": "Toner B",
                    "Cantidad": 2,
                    "Total Linea": 2000,
                    "Precio Un.": 1000,
                },
                {
                    "Folio": 200,
                    "SKU": "C",
                    "Producto": "Toner C",
                    "Cantidad": 1,
                    "Total Linea": 3000,
                    "Precio Un.": 3000,
                },
                {
                    "Folio": 200,
                    "SKU": "C",
                    "Producto": "Toner C",
                    "Cantidad": 1,
                    "Total Linea": 3000,
                    "Precio Un.": 3000,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        metrics = build_document_quality_metrics(df, detection)
        warnings = build_quality_warnings(df, detection)

        self.assertEqual(metrics.total_unique_documents, 2)
        self.assertEqual(metrics.multiline_documents, 1)
        self.assertEqual(metrics.possible_exact_duplicates, 1)
        self.assertEqual(metrics.possible_exact_duplicate_rows, 2)
        self.assertFalse(
            any("duplicados exactos" in warning for warning in warnings)
        )

    def test_multiline_document_does_not_create_warning_by_itself(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "SKU": "A",
                    "Cantidad": 1,
                    "Total Linea": 1000,
                    "Precio Un.": 1000,
                },
                {
                    "Folio": 100,
                    "SKU": "B",
                    "Cantidad": 2,
                    "Total Linea": 2000,
                    "Precio Un.": 1000,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        metrics = build_document_quality_metrics(df, detection)
        warnings = build_quality_warnings(df, detection)

        self.assertEqual(metrics.total_unique_documents, 1)
        self.assertEqual(metrics.multiline_documents, 1)
        self.assertEqual(metrics.possible_exact_duplicates, 0)
        self.assertEqual(metrics.possible_exact_duplicate_rows, 0)
        self.assertFalse(
            any("documentos repetidos" in warning.lower() for warning in warnings)
        )

    def test_possible_exact_duplicate_examples_use_expected_columns(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 200,
                    "Razon Social": "Cliente A",
                    "Fecha": "2026-01-01",
                    "SKU": "C",
                    "Producto": "Toner C",
                    "Cantidad": 1,
                    "Total Linea": 3000,
                    "Precio Un.": 3000,
                },
                {
                    "Folio": 200,
                    "Razon Social": "Cliente A",
                    "Fecha": "2026-01-01",
                    "SKU": "C",
                    "Producto": "Toner C",
                    "Cantidad": 1,
                    "Total Linea": 3000,
                    "Precio Un.": 3000,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        examples = build_possible_exact_duplicate_examples(df, detection)

        self.assertEqual(
            list(examples.columns),
            [
                "documento",
                "cliente",
                "fecha",
                "SKU",
                "producto",
                "cantidad",
                "monto linea",
                "precio unitario",
            ],
        )
        self.assertEqual(len(examples), 2)

    def test_uses_product_when_sku_is_empty_per_row(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "SKU": None,
                    "Producto": "Toner A",
                    "Cantidad": 1,
                    "Total Linea": 1000,
                    "Precio Un.": 1000,
                },
                {
                    "Folio": 100,
                    "SKU": None,
                    "Producto": "Toner B",
                    "Cantidad": 1,
                    "Total Linea": 1000,
                    "Precio Un.": 1000,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        metrics = build_document_quality_metrics(df, detection)

        self.assertEqual(metrics.multiline_documents, 1)
        self.assertEqual(metrics.possible_exact_duplicates, 0)
        self.assertEqual(metrics.possible_exact_duplicate_rows, 0)

    def test_same_sku_with_different_product_is_multiline_not_exact_duplicate(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "SKU": "NC-HP 964XLC",
                    "Producto": "Tinta HP 964 XL Amarillo",
                    "Cantidad": 1,
                    "Total Linea": 30244,
                    "Precio Un.": 30243.6975,
                },
                {
                    "Folio": 100,
                    "SKU": "NC-HP 964XLC",
                    "Producto": "Tinta HP 964 XL Magenta",
                    "Cantidad": 1,
                    "Total Linea": 30244,
                    "Precio Un.": 30243.6975,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        metrics = build_document_quality_metrics(df, detection)

        self.assertEqual(metrics.multiline_documents, 1)
        self.assertEqual(metrics.possible_exact_duplicates, 0)
        self.assertEqual(metrics.possible_exact_duplicate_rows, 0)

    def test_empty_sku_lines_stay_in_customer_views_not_product_views(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "Razon Social": "Cliente A",
                    "Fecha": "2026-01-01",
                    "SKU": "SKU-1",
                    "Producto": "Toner A",
                    "Cantidad": 1,
                    "Total Linea": 1000,
                    "Costo Venta Total": 600,
                    "Margen Contrib $": 400,
                },
                {
                    "Folio": 101,
                    "Razon Social": "Cliente B",
                    "Fecha": "2026-01-02",
                    "SKU": None,
                    "Producto": "Ajuste especial",
                    "Cantidad": 1,
                    "Total Linea": 500,
                    "Costo Venta Total": 300,
                    "Margen Contrib $": 200,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        datasets = build_analysis_datasets(df, detection)
        coverage = build_sku_coverage_metrics(df, detection)

        self.assertEqual(len(datasets["dataset_base"]), 2)
        self.assertEqual(len(datasets["dataset_cliente"]), 2)
        self.assertEqual(len(datasets["dataset_producto_sku"]), 1)
        self.assertEqual(len(datasets["dataset_rentabilidad_cliente"]), 2)
        self.assertEqual(len(datasets["dataset_rentabilidad_producto_sku"]), 1)
        self.assertEqual(coverage.empty_sku_rows, 1)
        self.assertEqual(coverage.empty_sku_with_profitability_rows, 1)
        self.assertEqual(coverage.empty_sku_with_profitability_sales, 500)
        self.assertEqual(coverage.empty_sku_profitability_amount, 200)

    def test_empty_sku_examples_include_expected_columns(self):
        df = pd.DataFrame(
            [
                {
                    "Documento": "Factura Electronica",
                    "Folio": 101,
                    "Razon Social": "Cliente B",
                    "Fecha": "2026-01-02",
                    "SKU": "(no aplica)",
                    "Producto": "Ajuste especial",
                    "Cantidad": 1,
                    "Total Linea": 500,
                    "Costo Venta Total": 300,
                    "Margen Contrib $": 200,
                    "Vendedor": "Ejecutiva A",
                }
            ]
        )
        detection = detect_key_columns(df.columns)

        examples = build_empty_sku_examples(df, detection)

        self.assertEqual(
            list(examples.columns),
            [
                "Documento",
                "Folio",
                "Cliente",
                "Fecha",
                "Producto/descripcion",
                "Cantidad",
                "Monto linea",
                "Costo",
                "Margen/utilidad",
                "Vendedor",
            ],
        )
        self.assertEqual(len(examples), 1)

    def test_profitability_coverage_excludes_lines_without_cost_or_margin(self):
        df = pd.DataFrame(
            [
                {
                    "Folio": 100,
                    "Razon Social": "Cliente A",
                    "SKU": "SKU-1",
                    "Producto": "Toner A",
                    "Total Linea": 1000,
                    "Costo Venta Total": 600,
                    "Margen Contrib $": 400,
                },
                {
                    "Folio": 101,
                    "Razon Social": "Cliente B",
                    "SKU": "SKU-2",
                    "Producto": "Toner B",
                    "Total Linea": 500,
                    "Costo Venta Total": 0,
                    "Margen Contrib $": None,
                },
                {
                    "Folio": 102,
                    "Razon Social": "Cliente C",
                    "SKU": None,
                    "Producto": "Ajuste",
                    "Total Linea": 300,
                    "Costo Venta Total": None,
                    "Margen Contrib $": -50,
                },
            ]
        )
        detection = detect_key_columns(df.columns)

        metrics = build_profitability_coverage_metrics(df, detection)
        datasets = build_analysis_datasets(df, detection)

        self.assertEqual(metrics.total_rows, 3)
        self.assertEqual(metrics.valid_sales_amount_rows, 3)
        self.assertEqual(metrics.valid_cost_rows, 1)
        self.assertEqual(metrics.valid_margin_rows, 2)
        self.assertEqual(metrics.zero_cost_rows, 1)
        self.assertEqual(metrics.null_cost_rows, 1)
        self.assertEqual(metrics.null_margin_rows, 1)
        self.assertEqual(metrics.negative_margin_rows, 1)
        self.assertEqual(len(datasets["dataset_cliente"]), 3)
        self.assertEqual(len(datasets["dataset_rentabilidad_cliente"]), 2)
        self.assertEqual(len(datasets["dataset_rentabilidad_producto_sku"]), 1)
        self.assertEqual(len(datasets["dataset_sin_costo"]), 1)

    def test_missing_profitability_examples_include_expected_columns(self):
        df = pd.DataFrame(
            [
                {
                    "Documento": "Factura Electronica",
                    "Folio": 101,
                    "Razon Social": "Cliente B",
                    "Fecha": "2026-01-02",
                    "SKU": "SKU-2",
                    "Producto": "Toner B",
                    "Cantidad": 1,
                    "Total Linea": 500,
                    "Costo Venta Total": 0,
                    "Margen Contrib $": None,
                    "Vendedor": "Ejecutiva A",
                }
            ]
        )
        detection = detect_key_columns(df.columns)

        examples = build_missing_profitability_examples(df, detection)

        self.assertEqual(
            list(examples.columns),
            [
                "Documento",
                "Folio",
                "Cliente",
                "Fecha",
                "SKU",
                "Producto",
                "Cantidad",
                "Monto linea",
                "Costo",
                "Margen/utilidad",
                "Vendedor",
            ],
        )
        self.assertEqual(len(examples), 1)


if __name__ == "__main__":
    unittest.main()
