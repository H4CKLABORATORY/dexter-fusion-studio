#!/usr/bin/env python3
"""Descarga histórica de dos loterías desde NY State Gaming Commission (CSV público).
Sin tokens/API keys, sin estadísticas predictivas ni datos fabricados.
"""
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'powerball': ('d6yy-54nr', 'https://data.ny.gov/d/d6yy-54nr', '2010-02-03', '2015-10-07', 69, 26),
    'megamillions': ('5xaw-6ayf', 'https://data.ny.gov/d/5xaw-6ayf', '2002-05-17', '2025-04-08', 70, 24)
}


def parse_row(game, row):
    date = str(row.get('Draw Date') or row.get('draw_date') or '').strip()[:10]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        # Socrata CSV normally uses ISO 8601 timestamp; optionally accept US dates.
        try: date = datetime.strptime(date, '%m/%d/%Y').strftime('%Y-%m-%d')
        except ValueError: return None
    try: datetime.strptime(date, '%Y-%m-%d')
    except ValueError: return None
    values = re.findall(r'\d+', str(row.get('Winning Numbers') or row.get('winning_numbers') or ''))
    if game == 'powerball':
        if len(values) != 6: return None
        main = [int(v) for v in values[:5]]
        bonus = int(values[5])
        # In the past the matrix differed, do not reject historic draws under new rules.
        if not(1<=min(main)<=max(main)<=69 and 1<=bonus<=39): return None
    else:
        if len(values) != 5: return None
        main = [int(v) for v in values]
        special = str(row.get('Mega Ball') or row.get('mega_ball') or '').strip()
        if not re.fullmatch(r'\d{1,2}', special): return None
        bonus = int(special)
        if not(1<=min(main)<=max(main)<=75 and 1<=bonus<=52): return None
    if len(set(main))!=5:return None
    return [date, *sorted(main), bonus]


def normalize(game, csv_text):
    parsed = csv.DictReader(io.StringIO(csv_text.lstrip('\ufeff')))
    if not parsed.fieldnames or not any('date' in field.lower() for field in parsed.fieldnames):
        raise ValueError('CSV no tiene columnas reconocibles')
    rows={}
    skipped=0
    for item in parsed:
        parsed_row=parse_row(game,item)
        if not parsed_row: skipped+=1;continue
        date=parsed_row[0]
        if date in rows and rows[date]!=parsed_row:
            raise ValueError(f'Conflicto de números para la fecha {date}')
        rows[date]=parsed_row
    output=sorted(rows.values(),key=lambda r:r[0],reverse=True)
    if not output:raise ValueError('No hay datos históricos válidos')
    return output, skipped


def fetch_csv(dataset_id):
    url=f'https://data.ny.gov/api/v3/views/{dataset_id}/export.csv?accessType=DOWNLOAD'
    req=Request(url, headers={'User-Agent':'LottoLabDexter/2.0 historical statistics educational project', 'Accept':'text/csv'})
    with urlopen(req,timeout=80) as response:
        content=response.read(6_000_000)
    if not content or len(content)>=6_000_000:raise ValueError('Tamaño de CSV inválido')
    return content.decode('utf-8-sig')


def write_datasets(output, fetcher=fetch_csv, now=None):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    now=now or datetime.now(timezone.utc)
    summaries={}
    for game,(ident,homepage,start,current,mmax,bmax) in SOURCES.items():
        rows,skipped=normalize(game,fetcher(ident))
        # Detect structurally implausible truncation due to API limits.
        oldest=rows[-1][0]
        if oldest>start:
            raise ValueError(f'{game}: el historial se truncó; inicio {oldest} > {start}')
        current_rows=sum(1 for r in rows if r[0]>=current)
        if current_rows<20:raise ValueError(f'{game}: faltan sorteos del régimen actual')
        record={
            'schema':2,'game':game,'source':homepage,'provider':'New York State Gaming Commission / NY Open Data',
            'refreshed_at':now.isoformat(), 'last_draw':rows[0][0],
            'first_draw':rows[-1][0], 'count':len(rows),'current_rule_from':current,
            'current_main_max':mmax,'current_bonus_max':bmax,'skipped_rows':skipped,
            'rows':rows
        }
        (output/f'{game}.json').write_text(json.dumps(record,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        summaries[game]={k:record[k] for k in ['source','provider','refreshed_at','first_draw','last_draw','count','current_rule_from','skipped_rows']}
        print(game, 'rows',len(rows),'current',current_rows,'oldest',oldest,'latest',rows[0][0], 'skipped',skipped)
    (output/'metadata.json').write_text(json.dumps(summaries,indent=2,ensure_ascii=False),encoding='utf-8')
    return summaries


if __name__=='__main__':
    try:write_datasets(sys.argv[1] if len(sys.argv)>1 else ROOT/'data')
    except Exception as exc:
        print(f'ERROR descargando datos oficiales: {exc}',file=sys.stderr)
        raise SystemExit(1)