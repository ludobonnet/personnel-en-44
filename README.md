# Dashboard Personnels / Collèges publics 44

## Intérêt
- Visualiser les personnels (vie scolaire, enseignants) et les élèves des collèges publics de Loire-Atlantique (académie de Nantes), avec IPS et effectifs spécifiques (Segpa, ULIS).
- Tableaux filtrables/triables, métriques synthétiques, sources explicites.
- Publisable sur GitHub Pages via le workflow fourni.

## Sources de données
- Indicateurs personnels : [Les personnels dans les établissements du second degré](https://www.data.gouv.fr/datasets/les-personnels-dans-les-etablissements-du-second-degre/)
- Effectifs élèves collège : [Effectifs d’élèves par niveau… (octobre)](https://www.data.gouv.fr/datasets/effectifs-deleves-par-niveau-sexe-langues-vivantes-1-et-2-les-plus-frequentes-par-college-date-dobservation-au-debut-du-mois-doctobre-chaque-annee/)
- IPS : [Indices de position sociale des collèges (à partir de 2023)](https://www.data.gouv.fr/datasets/ips-colleges-a-partir-de-2023/)

## Génération locale
```bash
python3 generate_dashboard.py \
  --indicateurs fr-en-indicateurs_personnels_etablissements2d.csv \
  --effectifs "Effectifs Collège FR-EN.csv" \
  --ips "Indices de position sociale collèges 2023.csv" \
  --output dashboard.html
```
Ouvrir `dashboard.html` dans un navigateur.

## Déploiement GitHub Pages (branche main)
- Workflow : `.github/workflows/deploy.yml`
- Sortie : `dist/index.html`
- Activer Pages avec source “GitHub Actions” dans les paramètres du dépôt.

## Auteur
Ludovic Bonnet

## Licence
Ce projet est sous licence CC BY-NC 4.0 (voir `LICENSE`). Réutilisation autorisée, usage commercial interdit.

