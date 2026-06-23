import unittest

import pandas as pd

from src.core.commercial_agenda import build_commercial_agenda
from src.core.column_detector import detect_key_columns


class CommercialAgendaTests(unittest.TestCase):
    def setUp(self):
        self.alerts = pd.DataFrame(
            [
                {
                    "cliente": "Critico caida",
                    "venta_total": 1000,
                    "participacion": 0.30,
                    "variacion_porcentual": -0.40,
                    "tendencia": "En caida",
                    "alerta_comercial": "Alerta critica",
                    "cliente_critico": True,
                    "recomendacion_sugerida": "Revisar",
                },
                {
                    "cliente": "Relevante inactivo",
                    "venta_total": 500,
                    "participacion": 0.08,
                    "variacion_porcentual": None,
                    "tendencia": "Inactivo",
                    "alerta_comercial": "Alerta relevante",
                    "cliente_critico": False,
                    "recomendacion_sugerida": "Contactar",
                },
                {
                    "cliente": "Nuevo",
                    "venta_total": 300,
                    "participacion": 0.04,
                    "variacion_porcentual": None,
                    "tendencia": "Nuevo",
                    "alerta_comercial": "Oportunidad",
                    "cliente_critico": False,
                    "recomendacion_sugerida": "Monitorear",
                },
                {
                    "cliente": "Estable",
                    "venta_total": 100,
                    "participacion": 0.01,
                    "variacion_porcentual": 0.05,
                    "tendencia": "Estable",
                    "alerta_comercial": "Sin alerta",
                    "cliente_critico": False,
                    "recomendacion_sugerida": "Mantener",
                },
            ]
        )

    def test_assigns_priority_action_and_deadline(self):
        result = build_commercial_agenda(self.alerts, median_client_sales=200)
        agenda = result.agenda.set_index("cliente")

        self.assertEqual(agenda.loc["Critico caida", "prioridad_gestion"], "Alta")
        self.assertEqual(
            agenda.loc["Critico caida", "tipo_sugerencia"],
            "Revisar cliente critico",
        )
        self.assertEqual(agenda.loc["Critico caida", "plazo_sugerido"], "Inmediato")
        self.assertEqual(agenda.loc["Relevante inactivo", "prioridad_gestion"], "Media")
        self.assertEqual(
            agenda.loc["Nuevo", "tipo_sugerencia"],
            "Evaluar desarrollo comercial",
        )
        self.assertEqual(agenda.loc["Estable", "prioridad_gestion"], "Baja")
        self.assertEqual(
            agenda.loc["Critico caida", "validacion_requerida_crm"],
            "Revisar si existe gestion, llamada, cotizacion o tarea abierta en CRM.",
        )
        self.assertIn(
            "Representa 30,0% de la venta y cayo 40,0%",
            agenda.loc["Critico caida", "por_que_importa"],
        )

    def test_orders_high_priority_and_immediate_first(self):
        result = build_commercial_agenda(self.alerts, median_client_sales=200)

        self.assertEqual(result.agenda.iloc[0]["cliente"], "Critico caida")
        self.assertEqual(result.high_priority_actions, 1)
        self.assertEqual(result.immediate_actions, 1)
        self.assertEqual(result.this_week_actions, 1)

    def test_assigns_seller_from_each_clients_latest_sale(self):
        sales = pd.DataFrame(
            [
                {"Cliente": "Critico caida", "Fecha": "01/01/2026", "Vendedor": "Ana"},
                {"Cliente": "Critico caida", "Fecha": "15/02/2026", "Vendedor": "Luis"},
                {"Cliente": "Nuevo", "Fecha": "10/02/2026", "Vendedor": "Maria"},
                {"Cliente": "Nuevo", "Fecha": "20/02/2026", "Vendedor": None},
            ]
        )
        result = build_commercial_agenda(
            self.alerts,
            median_client_sales=200,
            sales_df=sales,
            detection=detect_key_columns(sales.columns),
        )
        agenda = result.agenda.set_index("cliente")

        self.assertEqual(
            agenda.loc["Critico caida", "vendedor_responsable_sugerido"],
            "Luis",
        )
        self.assertEqual(
            agenda.loc["Nuevo", "vendedor_responsable_sugerido"],
            "Sin vendedor identificado",
        )


if __name__ == "__main__":
    unittest.main()
