# Backoffice MRR - Gauss Control

Pequeña herramienta en línea de comando para monitorear el MRR de Gauss Control y generar reportes mensuales de facturación.

## Requisitos
- Python 3.10 o superior

## Datos de ejemplo
El archivo `data/subscriptions.json` incluye una muestra de suscripciones con los campos:
- `customer`: nombre del cliente.
- `plan`: plan contratado.
- `monthly_amount`: monto mensual en USD.
- `start_date` y `end_date`: fechas en formato `YYYY-MM-DD` (usar `null` si el contrato sigue vigente).
- `notes`: anotaciones operativas.

Puedes editar ese JSON o apuntar a otro archivo con `--data`.

## Uso rápido
Mostrar el MRR del mes actual:
```bash
python backoffice.py summary
```

Consultar un mes específico:
```bash
python backoffice.py summary --month 2024-09
```

Generar un reporte CSV para facturación:
```bash
python backoffice.py report --month 2024-09 --output reports
```
El archivo se guardará como `reports/gauss_mrr_<año>_<mes>.csv` y contendrá solo las suscripciones activas en ese mes.

## Sugerencias
- Revisa el desglose por plan para detectar caídas o upgrades.
- Agrega campos adicionales al JSON (por ejemplo `currency` o `payment_terms`) si necesitas enriquecer los reportes.
