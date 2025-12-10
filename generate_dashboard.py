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
    Compatible avec deux schémas :
    - fr-en-effectifs-second-degre.csv
    - Effectifs Collège FR-EN.csv
    """
    latest: Dict[str, dict] = {}

    def pick(keys, fallback=None):
        for k in keys:
            if k in reader.fieldnames:
                return k
        return fallback

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames:
            return latest

        year_key = pick(["Rentrée scolaire", "Annee_scolaire", "\ufeffAnnee_scolaire"], reader.fieldnames[0])
        dep_key = pick(["Code_departement", "Code département"])
        acad_key = pick(["Academie", "Académie"])
        type_key = pick(["Type_d_etablissement", "Dénomination principale"])
        secteur_key = pick(["Secteur_d_enseignement", "Secteur"])
        uai_key = pick(["Numero_d_etablissement", "UAI"])
        eleves_key = pick(["Nombre_d_eleves", "nombre_eleves_total"])
        commune_key = pick(["localite_acheminement", "Commune"])
        segpa_key = pick(["Nombre d'élèves total Segpa", "Nombre_eleves_total_Segpa"])
        ulis_key = pick(["Nombre d'élèves total ULIS", "Nombre_eleves_total_ULIS"])

        for r in reader:
            dep_val = (r.get(dep_key) or "").zfill(3)
            if dep_val != f"{departement:0>3}":
                continue
            if (r.get(acad_key) or "").upper() != academie.upper():
                continue
            type_val = (r.get(type_key) or "").strip().upper()
            if type_val != "COLLEGE":
                continue
            if (r.get(secteur_key) or "").strip().lower() != "public":
                continue
            uai = r.get(uai_key)
            if not uai:
                continue
            year = r.get(year_key, "")
            prev = latest.get(uai)
            if prev and year <= prev["year"]:
                continue
            try:
                eleves = int(r.get(eleves_key) or 0)
            except (TypeError, ValueError):
                eleves = None
            try:
                segpa = int(r.get(segpa_key) or 0) if segpa_key else None
            except (TypeError, ValueError):
                segpa = None
            try:
                ulis = int(r.get(ulis_key) or 0) if ulis_key else None
            except (TypeError, ValueError):
                ulis = None
            latest[uai] = {
                "year": year,
                "eleves": eleves,
                "commune": r.get(commune_key),
                "segpa": segpa,
                "ulis": ulis,
            }
    return latest


def load_ips(
    path: Optional[pathlib.Path],
    departement: str,
    academie: str,
) -> Dict[str, dict]:
    """
    Charge l'IPS et l'écart-type par UAI depuis le fichier d'indices sociaux.
    Filtre : département, académie, secteur public.
    """
    ips_map: Dict[str, dict] = {}
    if not path:
        return ips_map
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        if not reader.fieldnames:
            return ips_map
        def pick(keys, fallback=None):
            for k in keys:
                if k in reader.fieldnames:
                    return k
            return fallback
        dep_key = pick(["Code du département", "Code_departement"])
        acad_key = pick(["Académie", "Academie", "Code académie"])
        secteur_key = pick(["Secteur", "secteur"])
        uai_key = pick(["UAI"])
        ips_key = pick(["IPS"])
        ecart_key = pick(["Ecart type de l'IPS", "Ecart type IPS"])
        year_key = pick(["Rentrée scolaire"])
        for r in reader:
            if (r.get(dep_key) or "") != departement.zfill(2) and (r.get(dep_key) or "") != departement.zfill(3):
                continue
            if (r.get(acad_key) or "").upper() != academie.upper():
                continue
            if (r.get(secteur_key) or "").strip().lower().startswith("priv"):
                continue
            uai = r.get(uai_key)
            if not uai:
                continue
            ips_val = None
            ips_ecart = None
            try:
                ips_val = float(r.get(ips_key)) if r.get(ips_key) else None
            except (TypeError, ValueError):
                pass
            try:
                ips_ecart = float(r.get(ecart_key)) if r.get(ecart_key) else None
            except (TypeError, ValueError):
                pass
            ips_map[uai] = {"ips": ips_val, "ecart": ips_ecart, "year": r.get(year_key)}
    return ips_map


def merge_data(
    ind_rows: List[dict],
    eff_map: Dict[str, dict],
    ips_map: Dict[str, dict],
) -> Tuple[List[dict], dict]:
    indic_year = None
    for r in ind_rows:
        indic_year = r.get("Année de la rentrée scolaire") or r.get("Annee_scolaire") or r.get("Rentrée scolaire")
        if indic_year:
            break

    eff_year = None
    for v in eff_map.values():
        eff_year = v.get("year")
        if eff_year:
            break

    ips_year = None
    for v in ips_map.values():
        ips_year = v.get("year")
        if ips_year:
            break

    records: List[dict] = []
    for r in ind_rows:
        uai = r.get("Identifiant de l'établissement")
        eff = eff_map.get(uai)
        ips = ips_map.get(uai)
        try:
            aed = float(r["ETP de personnels de vie scolaire"]) if r["ETP de personnels de vie scolaire"] else None
        except (ValueError, KeyError):
            aed = None
        etp_enseignants = None
        try:
            etp_enseignants = float(r.get("ETP enseignants (hommes et femmes)") or 0)
        except (ValueError, TypeError):
            etp_enseignants = None
        eleves = eff.get("eleves") if eff else None
        effectifs_annee = eff.get("year") if eff else None
        commune = eff.get("commune") if eff else None
        segpa = eff.get("segpa") if eff else None
        ulis = eff.get("ulis") if eff else None
        ips_value = ips.get("ips") if ips else None
        ips_ecart = ips.get("ecart") if ips else None
        records.append(
            {
                "uai": uai,
                "nom": (r.get("Nom de l'établissement") or "").title(),
                "aed_etp": aed,
                "etp_enseignants": etp_enseignants,
                "eleves": eleves,
                "secteur": r.get("Secteur", ""),
                "effectifs_annee": effectifs_annee,
                "commune": commune,
                "segpa": segpa,
                "ulis": ulis,
                "ips": ips_value,
                "ips_ecart": ips_ecart,
            }
        )

    valid_aed = [x["aed_etp"] for x in records if isinstance(x["aed_etp"], (int, float))]
    valid_etp_ens = [x["etp_enseignants"] for x in records if isinstance(x["etp_enseignants"], (int, float))]
    valid_eleves = [x["eleves"] for x in records if isinstance(x["eleves"], int)]
    valid_segpa = [x["segpa"] for x in records if isinstance(x["segpa"], int)]
    valid_ulis = [x["ulis"] for x in records if isinstance(x["ulis"], int)]
    valid_ips = [x["ips"] for x in records if isinstance(x["ips"], (int, float))]

    summary = {
        "nb_colleges": len(records),
        "aed_total": round(sum(valid_aed), 2) if valid_aed else None,
        "aed_moyen": round(sum(valid_aed) / len(valid_aed), 2) if valid_aed else None,
        "aed_min": round(min(valid_aed), 2) if valid_aed else None,
        "aed_max": round(max(valid_aed), 2) if valid_aed else None,
        "etp_ens_total": round(sum(valid_etp_ens), 2) if valid_etp_ens else None,
        "etp_ens_moyen": round(sum(valid_etp_ens) / len(valid_etp_ens), 2) if valid_etp_ens else None,
        "eleves_total": sum(valid_eleves) if valid_eleves else None,
        "segpa_total": sum(valid_segpa) if valid_segpa else None,
        "ulis_total": sum(valid_ulis) if valid_ulis else None,
        "ips_moyen": round(sum(valid_ips) / len(valid_ips), 1) if valid_ips else None,
        "ips_min": round(min(valid_ips), 1) if valid_ips else None,
        "ips_max": round(max(valid_ips), 1) if valid_ips else None,
        "annee_indic": indic_year,
        "annee_eff": eff_year,
        "annee_ips": ips_year,
    }
    return records, summary


def render_html(records: List[dict], summary: dict, meta: dict, top_n: int) -> str:
    data_json = json.dumps({"records": records, "summary": summary}, ensure_ascii=False, indent=2)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>Dashboard Personnels – Collèges publics de Loire-Atlantique (académie de Nantes)</title>
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
        <h1>Dashboard – Personnels · Collèges publics de {meta['departement_label']} ({meta['departement']})</h1>
      </div>
    </div>

    <div id="cards-row1" class="grid"></div>
    <div id="cards-row2" class="grid"></div>
    <div id="cards-row3" class="grid"></div>
    <div id="years" style="margin-top:-8px; margin-bottom:16px;"></div>

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
            <th data-sort="eleves" style="cursor:pointer;">Élèves</th>
            <th>Segpa</th>
            <th>ULIS</th>
            <th data-sort="ips" style="cursor:pointer;">IPS</th>
            <th data-sort="ips_ecart" style="cursor:pointer;">Écart-type IPS</th>
            <th data-sort="etp_enseignants" style="cursor:pointer;">Enseignants (ETP)</th>
            <th data-sort="aed_etp" style="cursor:pointer;">Vie scolaire (ETP)</th>
            <th data-sort="ratio" style="cursor:pointer;">Ratio élèves / ETP</th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
    <div class="footnote">
      Note : seuls les établissements publics sont inclus. Les ETP « personnels de vie scolaire » comprennent principalement les AED (surveillants, assistants pédagogiques, assistants de prévention et de sécurité, assistants en préprofessionnalisation, etc.) et peuvent inclure les CPE ou d’autres personnels éducatifs selon la déclaration de l’établissement.
    </div>
    <div class="footnote">
      Sources :
      <ul>
        <li>Les personnels dans les établissements du second degré – <a href="https://www.data.gouv.fr/datasets/les-personnels-dans-les-etablissements-du-second-degre/">data.gouv.fr</a></li>
        <li>Effectifs d’élèves en collège – <a href="https://www.data.gouv.fr/datasets/effectifs-deleves-par-niveau-sexe-langues-vivantes-1-et-2-les-plus-frequentes-par-college-date-dobservation-au-debut-du-mois-doctobre-chaque-annee/">data.gouv.fr</a></li>
        <li>Indices de position sociale des collèges (à partir de 2023) – <a href="https://www.data.gouv.fr/datasets/ips-colleges-a-partir-de-2023/">data.gouv.fr</a></li>
      </ul>
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

    const cardsRow1 = [
      {{ label: 'Collèges', value: summary.nb_colleges }},
      {{ label: 'IPS moyen', value: formatFloat(summary.ips_moyen) }},
      {{ label: 'IPS min / max', value: `${{formatFloat(summary.ips_min)}} / ${{formatFloat(summary.ips_max)}}` }},
    ];
    const cardsRow2 = [
      {{ label: 'Élèves (total)', value: formatNumber(summary.eleves_total) }},
      {{ label: 'Segpa total', value: formatNumber(summary.segpa_total) }},
      {{ label: 'ULIS total', value: formatNumber(summary.ulis_total) }},
      {{ label: 'Enseignants · Total ETP', value: formatFloat(summary.etp_ens_total) }},
    ];
    const cardsRow3 = [
      {{ label: 'Vie scolaire · Total ETP', value: formatFloat(summary.aed_total) }},
      {{ label: 'Vie scolaire · ETP moyen', value: formatFloat(summary.aed_moyen) }},
      {{ label: 'Vie scolaire · Min / Max ETP', value: `${{formatFloat(summary.aed_min)}} / ${{formatFloat(summary.aed_max)}}` }},
      {{ label: 'Vie scolaire · Élèves par ETP', value: ratioElevesParAed ? formatFloat(ratioElevesParAed) : 'n.d.' }},
    ];

    const renderCards = (rootId, items) => {{
      const root = document.getElementById(rootId);
      root.innerHTML = items.map(c => `
        <div class="card">
          <div class="muted">${{c.label}}</div>
          <div class="value">${{c.value}}</div>
        </div>
      `).join('');
    }};

    renderCards('cards-row1', cardsRow1);
    renderCards('cards-row2', cardsRow2);
    renderCards('cards-row3', cardsRow3);

    const yearsRoot = document.getElementById('years');
    yearsRoot.innerHTML = `
      <div class="muted">
        Années sources : personnels ${{summary.annee_indic || 'n.d.'}} · effectifs ${{summary.annee_eff || 'n.d.'}} · IPS ${{summary.annee_ips || 'n.d.'}}
      </div>
    `;

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
          <td>${{formatNumber(r.eleves)}}</td>
          <td>${{formatNumber(r.segpa)}}</td>
          <td>${{formatNumber(r.ulis)}}</td>
          <td>${{formatFloat(r.ips)}}</td>
          <td>${{formatFloat(r.ips_ecart)}}</td>
          <td>${{formatFloat(r.etp_enseignants)}}</td>
          <td>${{formatFloat(r.aed_etp)}}</td>
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
    parser.add_argument("--ips", help="Chemin du CSV indices de position sociale (optionnel)")
    parser.add_argument("--output", default="dashboard.html", help="Chemin de sortie HTML")
    parser.add_argument("--departement", default="44", help="Code département (ex: 44)")
    parser.add_argument("--academie", default="NANTES", help="Libellé académie (ex: NANTES)")
    parser.add_argument("--nature-prefix", default="collège", help="Préfixe nature établissement à filtrer")
    parser.add_argument("--top", type=int, default=15, help="Nombre d’entrées dans le top graphique")
    args = parser.parse_args()

    ind_path = pathlib.Path(args.indicateurs)
    eff_path = pathlib.Path(args.effectifs)
    ips_path = pathlib.Path(args.ips) if args.ips else None

    ind_rows = load_indicateurs(ind_path, args.departement, args.academie, args.nature_prefix)
    eff_map = load_effectifs_latest(eff_path, args.departement, args.academie)
    ips_map = load_ips(ips_path, args.departement, args.academie)

    # Détection de la clé année (avec BOM possible)
    records, summary = merge_data(ind_rows, eff_map, ips_map)

    html = render_html(
        records,
        summary,
        meta={
            "departement": args.departement,
            "departement_label": "Loire-Atlantique",
            "academie": args.academie,
            "ind_path": ind_path.name,
            "eff_path": eff_path.name,
            "ips_path": ips_path.name if ips_path else "non fourni",
        },
        top_n=args.top,
    )

    output_path = pathlib.Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard généré : {output_path}")


if __name__ == "__main__":
    main()

