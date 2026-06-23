# PROYECTO ANALISIS CLIENTES

Aplicacion Python/Streamlit para diagnosticar la calidad de un Excel de ventas antes de crear informes ejecutivos.

## Objetivo de esta etapa

Leer un archivo Excel de ventas, detectar columnas clave y clasificar el maximo nivel de analisis posible segun la data real disponible.

> Kappo analiza el maximo nivel ejecutivo posible segun la calidad real del informe de ventas disponible.

## Estructura

```text
app.py
src/adapters/excel_reader.py
src/core/column_detector.py
src/core/data_quality.py
src/core/level_classifier.py
src/core/report_capabilities.py
src/models.py
requirements.txt
README.md
```

## Instalacion

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
streamlit run app.py
```

La app permite cargar un Excel manualmente o seleccionar un Excel existente en la carpeta del proyecto.

## Niveles de analisis

- Nivel 0: data insuficiente.
- Nivel 1: ventas por cliente.
- Nivel 2: ventas por cliente y periodo.
- Nivel 3: ventas por cliente, producto y cantidad.
- Nivel 4: rentabilidad comercial si existe costo, margen o utilidad.
