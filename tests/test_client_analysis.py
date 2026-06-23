import unittest

import pandas as pd

from src.core.client_analysis import build_client_analysis
from src.core.column_detector import detect_key_columns


class ClientAnalysisTests(unittest.TestCase):
    def test_builds_ranking_concentration_and_classification(self):
        df = pd.DataFrame(
            [
                {"Razon Social": "Cliente A", "Fecha": "01/01/2026", "Total Linea": 50},
                {"Razon Social": "Cliente B", "Fecha": "02/01/2026", "Total Linea": 30},
                {"Razon Social": "Cliente C", "Fecha": "03/01/2026", "Total Linea": 15},
                {"Razon Social": "Cliente D", "Fecha": "04/01/2026", "Total Linea": 5},
            ]
        )
        detection = detect_key_columns(df.columns)

        result = build_client_analysis(df, detection)

        self.assertEqual(result.total_clients, 4)
        self.assertEqual(result.total_sales, 100)
        self.assertEqual(result.clients_for_50_percent, 1)
        self.assertEqual(result.clients_for_70_percent, 2)
        self.assertEqual(result.clients_for_80_percent, 2)
        self.assertEqual(result.top_1_concentration, 0.50)
        self.assertEqual(result.top_5_concentration, 1.0)
        self.assertEqual(result.average_sales_per_client, 25)
        self.assertEqual(result.median_sales_per_client, 22.5)
        self.assertEqual(
            result.ranking["clasificacion_cliente"].tolist(),
            [
                "Cliente estrategico",
                "Cliente estrategico",
                "Cliente de bajo volumen",
                "Cliente de bajo volumen",
            ],
        )

    def test_excludes_invalid_dates_when_date_column_exists(self):
        df = pd.DataFrame(
            [
                {"Razon Social": "Cliente A", "Fecha": "01/01/2026", "Total Linea": 100},
                {"Razon Social": "Cliente B", "Fecha": "fecha invalida", "Total Linea": 200},
            ]
        )
        detection = detect_key_columns(df.columns)

        result = build_client_analysis(df, detection)

        self.assertEqual(result.total_clients, 1)
        self.assertEqual(result.total_sales, 100)


if __name__ == "__main__":
    unittest.main()
