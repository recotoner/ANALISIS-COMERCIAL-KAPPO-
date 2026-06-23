import unittest

from src.core.column_detector import detect_key_columns
from src.core.level_classifier import classify_analysis_level


class ColumnDetectionTests(unittest.TestCase):
    def test_detects_recotoner_sales_columns_with_expected_priority(self):
        columns = [
            "#",
            "Rut",
            "Razon Social",
            "Fecha",
            "Documento",
            "Folio",
            "Glosa",
            "Familia",
            "Producto",
            "SKU",
            "Cantidad Equivalente",
            "Cantidad",
            "Precio Un.",
            "Total Linea",
            "Costo Venta Unitario",
            "Margen Contrib $",
        ]

        detection = detect_key_columns(columns)

        self.assertEqual(detection.get("cliente").detected_column, "Razon Social")
        self.assertEqual(detection.get("documento_folio").detected_column, "Folio")
        self.assertEqual(detection.get("producto_descripcion").detected_column, "Producto")
        self.assertEqual(detection.get("cantidad").detected_column, "Cantidad")
        self.assertEqual(detection.get("categoria_familia").detected_column, "Familia")
        self.assertEqual(classify_analysis_level(detection).level, 4)


if __name__ == "__main__":
    unittest.main()
