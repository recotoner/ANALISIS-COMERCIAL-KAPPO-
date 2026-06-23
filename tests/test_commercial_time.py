import unittest

import pandas as pd

from src.core.column_detector import detect_key_columns
from src.core.commercial_time import build_commercial_time_intelligence


class CommercialTimeTests(unittest.TestCase):
    def setUp(self):
        rows = []
        for date, document in [
            ("05/01/2026", "A1"),
            ("05/02/2026", "A2"),
            ("05/03/2026", "A3"),
            ("05/04/2026", "A4"),
        ]:
            rows.append(
                {
                    "Cliente": "Regular",
                    "Fecha": date,
                    "Total": 100,
                    "Folio": document,
                    "Vendedor": "Ana",
                }
            )
        rows.extend(
            [
                {
                    "Cliente": "Unica",
                    "Fecha": "15/03/2026",
                    "Total": 200,
                    "Folio": "U1",
                    "Vendedor": "Luis",
                },
                {
                    "Cliente": "Multilinea",
                    "Fecha": "01/04/2026",
                    "Total": 50,
                    "Folio": "M1",
                    "Vendedor": "Maria",
                },
                {
                    "Cliente": "Concentradas",
                    "Fecha": "01/04/2026",
                    "Total": 90,
                    "Folio": "C1",
                    "Vendedor": "Pedro",
                },
                {
                    "Cliente": "Frontera de mes",
                    "Fecha": "31/01/2026",
                    "Total": 80,
                    "Folio": "F1",
                    "Vendedor": "Sofia",
                },
                {
                    "Cliente": "Frontera de mes",
                    "Fecha": "01/02/2026",
                    "Total": 120,
                    "Folio": "F2",
                    "Vendedor": "Sofia",
                },
                {
                    "Cliente": "Concentradas",
                    "Fecha": "21/04/2026",
                    "Total": 110,
                    "Folio": "C2",
                    "Vendedor": "Pedro",
                },
                {
                    "Cliente": "Multilinea",
                    "Fecha": "01/04/2026",
                    "Total": 75,
                    "Folio": "M1",
                    "Vendedor": "Maria",
                },
            ]
        )
        self.sales = pd.DataFrame(rows)
        self.detection = detect_key_columns(self.sales.columns)

    def test_uses_median_interval_and_marks_overdue_cycle(self):
        result = build_commercial_time_intelligence(
            self.sales,
            self.detection,
            reference_date=pd.Timestamp("2026-06-01"),
        )
        clients = result.clients.set_index("cliente")

        self.assertEqual(clients.loc["Regular", "intervalo_mediano_dias"], 31)
        self.assertEqual(
            clients.loc["Regular", "intervalo_mensual_mediano_dias"],
            31,
        )
        self.assertGreaterEqual(
            clients["intervalo_mensual_mediano_dias"].dropna().min(),
            28,
        )
        self.assertEqual(
            clients.loc["Regular", "proxima_compra_esperada"],
            pd.Timestamp("2026-05-06"),
        )
        self.assertEqual(clients.loc["Regular", "dias_atraso"], 26)
        self.assertEqual(clients.loc["Regular", "confianza_recompra"], "Alta")
        self.assertEqual(
            clients.loc["Regular", "categoria_recompra"],
            "Recompra esperada atrasada",
        )
        self.assertEqual(
            clients.loc["Regular", "lectura_comercial_patron"],
            "Ciclo consistente",
        )
        self.assertEqual(
            clients.loc["Regular", "sugerencia_por_tiempo"],
            "Revisar recuperación comercial.",
        )
        self.assertEqual(result.overdue_clients, 1)

    def test_marks_single_purchase_as_insufficient_and_deduplicates_document_lines(self):
        result = build_commercial_time_intelligence(
            self.sales,
            self.detection,
            reference_date=pd.Timestamp("2026-06-01"),
        )
        clients = result.clients.set_index("cliente")

        self.assertEqual(clients.loc["Unica", "confianza_recompra"], "Insuficiente")
        self.assertEqual(clients.loc["Multilinea", "cantidad_compras"], 1)
        self.assertEqual(
            clients.loc["Multilinea", "confianza_recompra"],
            "Insuficiente",
        )
        self.assertEqual(
            clients.loc["Multilinea", "vendedor_responsable_sugerido"],
            "Maria",
        )
        self.assertEqual(
            clients.loc["Concentradas", "lectura_comercial_patron"],
            "Compras concentradas",
        )
        self.assertEqual(clients.loc["Concentradas", "cantidad_compras"], 1)
        self.assertEqual(
            clients.loc["Concentradas", "cantidad_documentos_compra"],
            2,
        )
        self.assertIn(
            "no permiten inferir ciclo estable",
            clients.loc["Concentradas", "sugerencia_por_tiempo"],
        )
        self.assertEqual(
            clients.loc["Frontera de mes", "intervalo_mediano_dias"],
            31,
        )
        self.assertEqual(
            clients.loc["Frontera de mes", "intervalo_mensual_mediano_dias"],
            31,
        )
        self.assertFalse(clients.loc["Frontera de mes", "recompra_atrasada"])


if __name__ == "__main__":
    unittest.main()
