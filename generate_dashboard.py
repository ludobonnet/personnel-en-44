#!/usr/bin/env python3
"""
Générateur de dashboard AED pour les collèges de Loire-Atlantique (44), académie de Nantes.

Entrées :
- fr-en-indicateurs_personnels_etablissements2d.csv (indicateurs personnels 2024)
- fr-en-effectifs-second-degre.csv (effectifs élèves)

Usage :
  python3 generate_dashboard.py \\
    --indicateurs fr-en-indicateurs_personnels_etablissements2d.csv \\
    --effectifs fr-en-effectifs-second-degre.csv \\
    --output dashboard.html

Arguments optionnels :
  --departement 44               Code département (par défaut 44)
  --academie NANTES              Libellé académie (par défaut NANTES)
  --nature-prefix collège        Prefix de nature établissement (filtre côté indicateurs)
  --top 15                       Nombre d’entrées dans le graphe Top ETP AED

Notes sur les personnels de vie scolaire (ETP) :
- Inclut principalement les assistants d’éducation (surveillants, assistants pédagogiques,
  assistants de prévention et de sécurité, assistants en préprofessionnalisation, etc.).
- Peut inclure les CPE et d’autres personnels éducatifs rattachés à la vie scolaire,
  selon la déclaration de l’établissement dans les bases de gestion.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
from typing import Dict, List, Optional, Tuple


def load_indicateurs(
    path: pathlib.Path,
    departement: str,
    academie: str,
    nature_prefix: str,
) -> List[dict]:
    rows: List[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            if r.get("Code département") != departement:
                continue
            if (r.get("Libellé académie") or "").upper() != academie.upper():
                continue
            if (r.get("Secteur") or "").strip().lower() != "public":
                continue
            nature = (r.get("Nature de l'établissement") or "").strip().lower()
            if not nature.startswith(nature_prefix.lower()):
                continue
            rows.append(r)
    return rows


def load_effectifs_latest(
    path: pathlib.Path,
    departement: str,
    academie: str,
) -> Dict[str, dict]:
    """
    Retourne, par UAI, la ligne d'effectifs la plus récente.
    """
    latest: Dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        # Gestion éventuelle du BOM sur la première clé
        year_key = reader.fieldnames[0] if reader.fieldnames else "\ufeffAnnee_scolaire"
        for r in reader:
            if r.get("Code_departement") != f"{departement:0>3}":
                continue
            if (r.get("Academie") or "").upper() != academie.upper():
                continue
            if (r.get("Type_d_etablissement") or "").strip().upper() != "COLLEGE":
                continue
            if (r.get("Secteur_d_enseignement") or "").strip().lower() != "public":
                continue
            uai = r.get("Numero_d_etablissement")
            if not uai:
                continue
            year = r.get(year_key, "")
            prev = latest.get(uai)
            if prev is None or year > prev.get(year_key, ""):
                latest[uai] = r
    return latest


def merge_data(
    ind_rows: List[dict],
    eff_map: Dict[str, dict],
    year_key: str,
) -> Tuple[List[dict], dict]:
    records: List[dict] = []
    for r in ind_rows:
        uai = r.get("Identifiant de l'établissement")
        eff = eff_map.get(uai)
        try:
            aed = float(r["ETP de personnels de vie scolaire"]) if r["ETP de personnels de vie scolaire"] else None
        except (ValueError, KeyError):
            aed = None
        eleves = None
        effectifs_annee = None
        if eff:
            try:
                eleves = int(eff.get("Nombre_d_eleves") or 0)
            except ValueError:
                eleves = None
            effectifs_annee = eff.get(year_key)
        commune = None
        if eff:
            commune = eff.get("localite_acheminement")
        records.append(
            {
                "uai": uai,
                "nom": (r.get("Nom de l'établissement") or "").title(),
                "aed_etp": aed,
                "eleves": eleves,
                "secteur": r.get("Secteur", ""),
                "effectifs_annee": effectifs_annee,
                "commune": commune,
            }
        )

    valid_aed = [x["aed_etp"] for x in records if isinstance(x["aed_etp"], (int, float))]
    valid_eleves = [x["eleves"] for x in records if isinstance(x["eleves"], int)]

    summary = {
        "nb_colleges": len(records),
        "aed_total": round(sum(valid_aed), 2) if valid_aed else None,
        "aed_moyen": round(sum(valid_aed) / len(valid_aed), 2) if valid_aed else None,
        "aed_min": round(min(valid_aed), 2) if valid_aed else None,
        "aed_max": round(max(valid_aed), 2) if valid_aed else None,
        "eleves_total": sum(valid_eleves) if valid_eleves else None,
    }
    return records, summary


def render_html(records: List[dict], summary: dict, meta: dict, top_n: int) -> str:
    data_json = json.dumps({"records": records, "summary": summary}, ensure_ascii=False, indent=2)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>Dashboard Personnels Vie Scolaire – Collèges 44 (académie de Nantes)</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f6f8fa;
      --card: #ffffff;
      --text: #222;
      --muted: #555;
      --accent: #2563eb;
      --accent-2: #16a34a;
      --border: #dce3ec;
      --shadow: 0 2px 8px rgba(0,0,0,0.08);
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
    }}
    body {{
      margin: 0;
      padding: 32px;
      background: var(--bg);
      color: var(--text);
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    h2 {{ margin: 24px 0 12px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 16px 0 24px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      box-shadow: var(--shadow);
    }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .value {{ font-size: 22px; font-weight: 700; }}
    .bar-chart {{
      display: grid;
      gap: 8px;
    }}
    .bar {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .bar-label {{ width: 220px; font-size: 13px; }}
    .bar-track {{
      flex: 1;
      background: #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
      height: 14px;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 8px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      position: sticky;
      top: 0;
      background: var(--card);
      z-index: 1;
    }}
    tbody tr:hover {{ background: rgba(37,99,235,0.08); }}
    .tag {{ padding: 2px 8px; border-radius: 999px; font-size: 12px; }}
    .tag.public {{ background: rgba(37,99,235,0.12); color: var(--accent); }}
    .tag.prive {{ background: rgba(16,185,129,0.12); color: #0f766e; }}
    .container {{ max-width: 1300px; margin: 0 auto; }}
    .top-bar {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
    .footnote {{ font-size: 12px; color: var(--muted); margin-top: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="top-bar">
      <div>
        <h1>Dashboard – Personnels de vie scolaire · Collèges de {meta['departement_label']} ({meta['departement']})</h1>
        <div class="muted">Académie de {meta['academie']} · Indicateurs personnels 2024 · Effectifs élèves (dernière année dispo trouvée)</div>
      </div>
      <div class="muted">Sources : {meta['ind_path']} & {meta['eff_path']}</div>
    </div>

    <div id="cards" class="grid"></div>

    <h2>Top {top_n} collèges publics par ETP (personnels vie scolaire)</h2>
    <div id="chart" class="card bar-chart"></div>

    <h2>Top {top_n} collèges publics par ratio élèves / ETP</h2>
    <div id="chart-ratio" class="card bar-chart"></div>

    <h2>Vue détaillée</h2>
    <div class="card" style="padding:12px; overflow:auto; max-height:650px;">
      <div style="display:flex; gap:8px; align-items:center; margin-bottom:8px;">
        <input id="filter-text" type="search" placeholder="Filtrer par collège ou commune" style="flex:1; padding:8px; border:1px solid var(--border); border-radius:8px;" />
      </div>
      <table>
        <thead>
          <tr>
            <th data-sort="nom" style="cursor:pointer;">Collège</th>
            <th data-sort="commune" style="cursor:pointer;">Commune</th>
            <th data-sort="aed_etp" style="cursor:pointer;">ETP</th>
            <th data-sort="eleves" style="cursor:pointer;">Élèves</th>
            <th data-sort="ratio" style="cursor:pointer;">Ratio élèves / ETP</th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
    <div class="footnote">
      Note : seuls les établissements publics sont inclus. Les ETP « personnels de vie scolaire » comprennent principalement les AED (surveillants, assistants pédagogiques, assistants de prévention et de sécurité, assistants en préprofessionnalisation, etc.) et peuvent inclure les CPE ou d’autres personnels éducatifs selon la déclaration de l’établissement.
    </div>
  </div>

  <script type="application/json" id="data-json">
{data_json}
  </script>

  <script>
    const payload = JSON.parse(document.getElementById('data-json').textContent);
    const records = payload.records;
    const summary = payload.summary;

    const formatNumber = (n) => n === null || n === undefined ? 'n.d.' : new Intl.NumberFormat('fr-FR').format(n);
    const formatFloat = (n) => n === null || n === undefined ? 'n.d.' : new Intl.NumberFormat('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}).format(n);

    const ratioElevesParAed = summary.aed_total && summary.eleves_total
      ? summary.eleves_total / summary.aed_total
      : null;

    const cards = [
      {{ label: 'Collèges', value: summary.nb_colleges }},
      {{ label: 'Total ETP', value: formatFloat(summary.aed_total) }},
      {{ label: 'ETP moyen', value: formatFloat(summary.aed_moyen) }},
      {{ label: 'Min / Max ETP', value: `${{formatFloat(summary.aed_min)}} / ${{formatFloat(summary.aed_max)}}` }},
      {{ label: 'Élèves (total)', value: formatNumber(summary.eleves_total) }},
      {{ label: 'Élèves par ETP', value: ratioElevesParAed ? formatFloat(ratioElevesParAed) : 'n.d.' }}
    ];

    const cardsRoot = document.getElementById('cards');
    cardsRoot.innerHTML = cards.map(c => `
      <div class="card">
        <div class="muted">${{c.label}}</div>
        <div class="value">${{c.value}}</div>
      </div>
    `).join('');

    const topChartData = records
      .filter(r => typeof r.aed_etp === 'number')
      .sort((a, b) => b.aed_etp - a.aed_etp)
      .slice(0, {top_n});

    const maxAed = Math.max(...topChartData.map(r => r.aed_etp));
    const chartRoot = document.getElementById('chart');
    chartRoot.innerHTML = topChartData.map(r => `
      <div class="bar">
        <div class="bar-label">${{r.nom}}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${{(r.aed_etp / maxAed) * 100}}%"></div>
        </div>
        <div class="muted" style="width:80px; text-align:right;">${{formatFloat(r.aed_etp)}} ETP</div>
      </div>
    `).join('');

    const ratioData = records
      .filter(r => typeof r.aed_etp === 'number' && typeof r.eleves === 'number' && r.aed_etp > 0)
      .map(r => ({{ nom: r.nom, aed_etp: r.aed_etp, eleves: r.eleves, ratio: r.eleves / r.aed_etp }}))
      .sort((a, b) => b.ratio - a.ratio)
      .slice(0, {top_n});

    const maxRatio = Math.max(...ratioData.map(r => r.ratio));
    const chartRatioRoot = document.getElementById('chart-ratio');
    chartRatioRoot.innerHTML = ratioData.map(r => `
      <div class="bar">
        <div class="bar-label">${{r.nom}}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${{(r.ratio / maxRatio) * 100}}%"></div>
        </div>
        <div class="muted" style="width:90px; text-align:right;">${{formatFloat(r.ratio)}} élèves/ETP</div>
      </div>
    `).join('');

    const tbody = document.getElementById('table-body');
    const filterInput = document.getElementById('filter-text');
    const headers = Array.from(document.querySelectorAll('th[data-sort]'));

    let sortKey = 'aed_etp';
    let sortDir = 'desc';

    const baseRows = records.map(r => ({{ 
      ...r,
      ratio: (typeof r.eleves === 'number' && typeof r.aed_etp === 'number' && r.aed_etp > 0)
        ? r.eleves / r.aed_etp
        : null,
    }}));

    const applySort = (rows) => {{
      const dir = sortDir === 'asc' ? 1 : -1;
      return rows.slice().sort((a, b) => {{
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (av < bv) return -1 * dir;
        if (av > bv) return 1 * dir;
        return 0;
      }});
    }};

    const applyFilter = () => {{
      const q = (filterInput.value || '').toLowerCase();
      return baseRows.filter(r => {{
        if (!q) return true;
        return (r.nom || '').toLowerCase().includes(q) || (r.commune || '').toLowerCase().includes(q);
      }});
    }};

    const renderTable = () => {{
      const filtered = applyFilter();
      const sorted = applySort(filtered);
      tbody.innerHTML = sorted.map(r => `
        <tr>
          <td>${{r.nom}}</td>
          <td>${{r.commune || 'n.d.'}}</td>
          <td>${{formatFloat(r.aed_etp)}} (2024)</td>
          <td>${{formatNumber(r.eleves)}} (${{r.effectifs_annee || 'n.d.'}})</td>
          <td>${{formatFloat(r.ratio)}}</td>
        </tr>
      `).join('');
    }};

    headers.forEach(h => {{
      h.addEventListener('click', () => {{
        const key = h.getAttribute('data-sort');
        if (sortKey === key) {{
          sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        }} else {{
          sortKey = key;
          sortDir = key === 'nom' || key === 'commune' ? 'asc' : 'desc';
        }}
        renderTable();
      }});
    }});

    filterInput.addEventListener('input', renderTable);
    renderTable();
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Générer le dashboard AED (collèges 44, académie Nantes).")
    parser.add_argument("--indicateurs", required=True, help="Chemin du CSV indicateurs personnels")
    parser.add_argument("--effectifs", required=True, help="Chemin du CSV effectifs second degré")
    parser.add_argument("--output", default="dashboard.html", help="Chemin de sortie HTML")
    parser.add_argument("--departement", default="44", help="Code département (ex: 44)")
    parser.add_argument("--academie", default="NANTES", help="Libellé académie (ex: NANTES)")
    parser.add_argument("--nature-prefix", default="collège", help="Préfixe nature établissement à filtrer")
    parser.add_argument("--top", type=int, default=15, help="Nombre d’entrées dans le top graphique")
    args = parser.parse_args()

    ind_path = pathlib.Path(args.indicateurs)
    eff_path = pathlib.Path(args.effectifs)

    ind_rows = load_indicateurs(ind_path, args.departement, args.academie, args.nature_prefix)
    eff_map = load_effectifs_latest(eff_path, args.departement, args.academie)

    # Détection de la clé année (avec BOM possible)
    with eff_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        headers = next(reader, [])
        year_key = headers[0] if headers else "\ufeffAnnee_scolaire"

    records, summary = merge_data(ind_rows, eff_map, year_key=year_key)

    html = render_html(
        records,
        summary,
        meta={
            "departement": args.departement,
            "departement_label": "Loire-Atlantique",
            "academie": args.academie,
            "ind_path": ind_path.name,
            "eff_path": eff_path.name,
        },
        top_n=args.top,
    )

    output_path = pathlib.Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard généré : {output_path}")


if __name__ == "__main__":
    main()

