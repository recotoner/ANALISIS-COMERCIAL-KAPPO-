import unittest

import pandas as pd

from src.commercial_pdf import build_executive_clients_pdf


class CommercialPdfTests(unittest.TestCase):
    def test_builds_pdf_from_commercial_outputs(self):
        summary = {
            "period_label": "01/01/2026 al 30/06/2026",
            "emission_date": "23/06/2026",
            "level_label": "Nivel 4",
            "general_quality": "Buena",
            "total_sales": 1000,
            "total_clients": 2,
            "top_5_concentration": 0.75,
            "top_10_concentration": 0.90,
            "clients_for_80_percent": 2,
            "risk_level": "Alto",
            "critical_alerts": 1,
            "relevant_alerts": 1,
            "opportunities": 1,
            "inactive_clients": 0,
            "high_priority_actions": 1,
            "medium_priority_actions": 1,
            "low_priority_actions": 0,
            "overdue_clients": 1,
            "normal_cycle_clients": 1,
            "reliable_clients": 2,
            "insufficient_history_clients": 0,
        }
        ranking = pd.DataFrame(
            [
                {
                    "cliente": "DATXER S.A.",
                    "venta_total": 700,
                    "participacion": 0.70,
                },
                {
                    "cliente": "TECNODATA",
                    "venta_total": 300,
                    "participacion": 0.30,
                },
            ]
        )
        agenda = pd.DataFrame(
            [
                {
                    "cliente": "DATXER S.A.",
                    "vendedor_responsable_sugerido": "Ana",
                    "venta_total": 700,
                    "participacion": 0.70,
                    "prioridad_gestion": "Alta",
                    "tipo_sugerencia": "Revisar cliente critico",
                    "alerta_comercial": "Alerta critica",
                    "motivo_comercial": "Caida reciente",
                    "validacion_requerida_crm": "Revisar CRM",
                }
            ]
        )
        commercial_time = pd.DataFrame(
            [
                {
                    "cliente": "DATXER S.A.",
                    "vendedor_responsable_sugerido": "Ana",
                    "categoria_recompra": "Recompra esperada atrasada",
                    "lectura_comercial_patron": "Ciclo consistente",
                    "sugerencia_por_tiempo": "Revisar recuperacion comercial.",
                    "ultima_compra": pd.Timestamp("2026-05-01"),
                    "proxima_compra_esperada": pd.Timestamp("2026-06-01"),
                    "dias_atraso": 22,
                    "confianza_recompra": "Alta",
                    "venta_total": 700,
                }
            ]
        )

        content = build_executive_clients_pdf(
            summary=summary,
            ranking=ranking,
            agenda=agenda,
            commercial_time_clients=commercial_time,
        )

        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 3000)


if __name__ == "__main__":
    unittest.main()
