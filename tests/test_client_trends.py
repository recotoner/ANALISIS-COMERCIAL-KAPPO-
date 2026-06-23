import unittest

import pandas as pd

from src.core.client_analysis import build_client_analysis
from src.core.client_trends import build_client_trend_analysis
from src.core.column_detector import detect_key_columns


class ClientTrendTests(unittest.TestCase):
    def test_detects_decline_new_inactive_and_growth(self):
        rows = []
        sales = {
            "Critico en caida": [100, 100, 100, 40, 40, 40],
            "Nuevo": [0, 0, 0, 30, 30, 30],
            "Inactivo": [50, 50, 50, 0, 0, 0],
            "En crecimiento": [20, 20, 20, 40, 40, 40],
            "Estable": [25, 25, 25, 25, 25, 25],
        }
        months = pd.period_range("2026-01", "2026-06", freq="M")
        for client, values in sales.items():
            for month, value in zip(months, values):
                if value:
                    rows.append(
                        {
                            "Razon Social": client,
                            "Fecha": month.to_timestamp(),
                            "Total Linea": value,
                        }
                    )
        df = pd.DataFrame(rows)
        detection = detect_key_columns(df.columns)
        base = build_client_analysis(df, detection)

        result = build_client_trend_analysis(df, detection, base)
        trends = result.client_alerts.set_index("cliente")["tendencia"].to_dict()

        self.assertEqual(result.detected_months, 6)
        self.assertEqual(trends["Critico en caida"], "En caida")
        self.assertEqual(trends["Nuevo"], "Nuevo")
        self.assertEqual(trends["Inactivo"], "Inactivo")
        self.assertEqual(trends["En crecimiento"], "En crecimiento")
        self.assertEqual(trends["Estable"], "Estable")
        self.assertGreaterEqual(result.critical_alerts, 1)
        self.assertGreaterEqual(result.opportunities, 1)

    def test_builds_monthly_totals_and_comparison(self):
        df = pd.DataFrame(
            [
                {
                    "Razon Social": "Cliente A",
                    "Fecha": pd.Timestamp(2026, month, 1),
                    "Total Linea": 100 if month <= 3 else 200,
                }
                for month in range(1, 7)
            ]
        )
        detection = detect_key_columns(df.columns)
        base = build_client_analysis(df, detection)

        result = build_client_trend_analysis(df, detection, base)

        self.assertEqual(result.previous_3_months_sales, 300)
        self.assertEqual(result.last_3_months_sales, 600)
        self.assertEqual(result.total_variation_percentage, 1.0)
        self.assertEqual(result.monthly_summary["venta_total"].sum(), 900)


if __name__ == "__main__":
    unittest.main()
