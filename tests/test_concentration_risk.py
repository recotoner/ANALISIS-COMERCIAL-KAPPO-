import unittest

import pandas as pd

from src.core.client_analysis import build_client_analysis
from src.core.column_detector import detect_key_columns
from src.core.concentration_risk import build_concentration_risk


def build_result(sales: list[float]):
    df = pd.DataFrame(
        {
            "Razon Social": [f"Cliente {index}" for index in range(len(sales))],
            "Total Linea": sales,
        }
    )
    detection = detect_key_columns(df.columns)
    return build_concentration_risk(build_client_analysis(df, detection))


class ConcentrationRiskTests(unittest.TestCase):
    def test_classifies_high_risk_and_critical_clients(self):
        result = build_result([30, 20, 15, 10, 10, 5, 4, 3, 2, 1])

        self.assertEqual(result.risk_level, "Alto")
        self.assertEqual(result.top_3_concentration, 0.65)
        self.assertEqual(result.principal_client_sales, 30)
        self.assertEqual(result.principal_client_share, 0.30)
        self.assertEqual(result.critical_clients.iloc[0]["nivel_criticidad"], "Critico")
        self.assertIn("concentracion alta", result.executive_summary)

    def test_classifies_medium_risk(self):
        result = build_result([8, 7, 6, 5, 4] + [3] * 5 + [2.75] * 20)

        self.assertEqual(result.risk_level, "Medio")

    def test_classifies_low_risk(self):
        result = build_result([1] * 30)

        self.assertEqual(result.risk_level, "Bajo")
        self.assertEqual(
            result.impact_message,
            "La venta se encuentra relativamente distribuida.",
        )


if __name__ == "__main__":
    unittest.main()
