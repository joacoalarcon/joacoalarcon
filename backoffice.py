"""Herramienta de backoffice para monitorear el MRR de Gauss Control.

Permite:
- Calcular el MRR del mes seleccionado.
- Obtener desglose por plan.
- Generar reportes CSV mensuales para facilitar los cobros.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DATE_FMT = "%Y-%m-%d"


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def parse_month(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "El mes debe tener el formato YYYY-MM (ej: 2024-11)"
        ) from exc


def month_window(target_month: dt.date) -> Tuple[dt.date, dt.date]:
    start = target_month.replace(day=1)
    next_month = start.replace(year=start.year + (start.month // 12), month=((start.month % 12) + 1))
    return start, next_month


def is_active_in_month(subscription: Dict, target_month: dt.date) -> bool:
    start, next_month = month_window(target_month)
    start_date = parse_date(subscription["start_date"])
    end_value = subscription.get("end_date")
    end_date = parse_date(end_value) if end_value else None

    has_started = start_date < next_month
    not_finished = end_date is None or end_date >= start
    return has_started and not_finished


def load_subscriptions(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def calculate_mrr(subscriptions: Iterable[Dict], target_month: dt.date) -> Dict:
    active = [s for s in subscriptions if is_active_in_month(s, target_month)]
    total = sum(s.get("monthly_amount", 0) for s in active)

    by_plan: Dict[str, float] = {}
    for item in active:
        plan = item.get("plan", "Sin plan")
        by_plan[plan] = by_plan.get(plan, 0) + item.get("monthly_amount", 0)

    return {"total": total, "by_plan": by_plan, "active_subscriptions": active}


def status_label(subscription: Dict, target_month: dt.date) -> str:
    end_value = subscription.get("end_date")
    if not end_value:
        return "Activa"

    end_date = parse_date(end_value)
    start, _ = month_window(target_month)
    return "Activa" if end_date >= start else "Cancelada"


def generate_report(subscriptions: Iterable[Dict], target_month: dt.date, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"gauss_mrr_{target_month.year}_{target_month.month:02d}.csv"
    destination = output_dir / file_name

    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Cliente",
                "Plan",
                "Monto Mensual (USD)",
                "Inicio",
                "Fin",
                "Estado",
                "Notas",
            ]
        )

        for item in subscriptions:
            if not is_active_in_month(item, target_month):
                continue

            writer.writerow(
                [
                    item.get("customer", ""),
                    item.get("plan", ""),
                    item.get("monthly_amount", 0),
                    item.get("start_date", ""),
                    item.get("end_date", ""),
                    status_label(item, target_month),
                    item.get("notes", ""),
                ]
            )

    return destination


def print_summary(mrr_result: Dict, target_month: dt.date) -> None:
    print(f"MRR para {target_month.strftime('%B %Y')}: ${mrr_result['total']:,.2f} USD")
    print(f"Suscripciones activas: {len(mrr_result['active_subscriptions'])}")
    print("\nDesglose por plan:")
    for plan, amount in sorted(mrr_result["by_plan"].items(), key=lambda x: x[0]):
        print(f"- {plan}: ${amount:,.2f} USD")


def command_summary(args: argparse.Namespace) -> None:
    month = args.month or dt.date.today().replace(day=1)
    subscriptions = load_subscriptions(args.data)
    mrr = calculate_mrr(subscriptions, month)
    print_summary(mrr, month)


def command_report(args: argparse.Namespace) -> None:
    month = args.month or dt.date.today().replace(day=1)
    subscriptions = load_subscriptions(args.data)
    mrr = calculate_mrr(subscriptions, month)
    destination = generate_report(mrr["active_subscriptions"], month, args.output)
    print_summary(mrr, month)
    print(f"\nReporte guardado en: {destination}")


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backoffice de MRR para Gauss Control",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/subscriptions.json"),
        help="Archivo JSON con las suscripciones",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_cmd = subparsers.add_parser("summary", help="Mostrar MRR del mes")
    summary_cmd.add_argument(
        "--month",
        type=parse_month,
        help="Mes objetivo en formato YYYY-MM",
    )
    summary_cmd.set_defaults(func=command_summary)

    report_cmd = subparsers.add_parser(
        "report", help="Generar reporte CSV para facturación"
    )
    report_cmd.add_argument(
        "--month",
        type=parse_month,
        help="Mes objetivo en formato YYYY-MM",
    )
    report_cmd.add_argument(
        "--output",
        type=Path,
        default=Path("reports"),
        help="Carpeta destino para el CSV",
    )
    report_cmd.set_defaults(func=command_report)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_cli()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
