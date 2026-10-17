#!/usr/bin/env python3
"""Biblioteca adicional: New York Take 5, dataset oficial dg63-4siq desde 1992.

Se almacenan sorteos matutinos y vespertinos como eventos distintos.
No se inventan resultados ni se mezclan modalidades de juego.
"""
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ID = "dg63-4siq"
SOURCE = "https://data.ny.gov/Government-Finance/Lottery-Take-5-Winning-Numbers-Beginning-1992/dg63-4siq"
CSV_URL = f"https://data.ny.gov/api/v3/views/{ID}/export.csv?accessType=DOWNLOAD"
PERIODS = (("midday", "Midday Winning Numbers", "midday_winning_numbers"),
           ("evening", "Evening Winning Numbers", "evening_winning_numbers"))


def canonical_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    for candidate in (value[:10], value):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def parse_numbers(value):
    values = re.findall(r"\d+", str(value or ""))
    if len(values) != 5:
        return None
    numbers = [int(v) for v in values]
    if len(set(numbers)) != 5 or not all(1 <= n <= 39 for n in numbers):
        return None
    return sorted(numbers)


def normalize(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV sin encabezados")
    records = {}
    skipped = 0
    for raw in reader:
        date = canonical_date(raw.get("Draw Date") or raw.get("draw_date"))
        if not date:
            skipped += 1
            continue
        for period, title, api in PERIODS:
            text = raw.get(title) or raw.get(api)
            if not str(text or "").strip():
                continue
            nums = parse_numbers(text)
            if nums is None:
                raise ValueError(f"Registro Take 5 inválido ({date}, {period})")
            key = (date, period)
            if key in records and records[key] != nums:
                raise ValueError(f"Sorteos contradictorios en {date}/{period}")
            records[key] = nums
    if not records:
        raise ValueError("No se hallaron sorteos oficiales Take 5")
    ordered = [
        {"date": date, "period": period, "main": values}
        for (date, period), values in sorted(records.items(), reverse=True)
    ]
    return ordered, skipped


def fetch_csv():
    request = Request(CSV_URL, headers={
        "Accept": "text/csv",
        "User-Agent": "LottoLabDexter/2.0 historical-public-data",
    })
    with urlopen(request, timeout=95) as response:
        content = response.read(9_000_000)
    if not content or len(content) >= 9_000_000:
        raise ValueError("CSV demasiado grande o vacío")
    return content.decode("utf-8-sig")


def write_dataset(destination, fetcher=fetch_csv, now=None):
    rows, skipped = normalize(fetcher())
    # Fuente oficial documenta historia desde 17-01-1992.
    if rows[-1]["date"] > "1992-01-17":
        raise ValueError("Archivo Take 5 truncado; falta el comienzo de 1992")
    if len(rows) < 3000:
        raise ValueError("Archivo Take 5 incompleto; faltan miles de sorteos")
    latest = rows[0]["date"]
    if latest < "2025-01-01":
        raise ValueError("Archivo Take 5 demasiado antiguo")
    record = {
        "schema": 3,
        "game": "nytake5",
        "source": SOURCE,
        "provider": "New York State Gaming Commission / NY Open Data",
        "refreshed_at": (now or datetime.now(timezone.utc)).isoformat(),
        "first_draw": rows[-1]["date"],
        "last_draw": latest,
        "count": len(rows),
        "current_main_max": 39,
        "draw_sessions": ["midday", "evening"],
        "skipped_rows": skipped,
        "rows": rows
    }
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    (output / "nytake5.json").write_text(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print("nytake5", "rows", len(rows), "first", record["first_draw"], "last", latest)
    return record


if __name__ == "__main__":
    try:
        base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data"
        write_dataset(base)
    except Exception as exc:
        print(f"ERROR en biblioteca oficial NY Take 5: {exc}", file=sys.stderr)
        raise SystemExit(1)
