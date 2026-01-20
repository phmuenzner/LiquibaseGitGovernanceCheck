
# Session-Verlauf – Liquibase Governance (Markdown)

Diese Markdown-Datei fasst unseren gesamten Arbeitsstand kompakt zusammen und kann direkt im Repo (z. B. `/docs/`) abgelegt werden.

---

## 1. Problemstellung
- Liquibase-Changelogs liegen in Git; einzelne Dateien enthalten mehrere Changesets.
- Governance-Regel für Pull Requests (PRs):
  - **Erlaubt**: neue Changesets oder Änderungen an bestehenden Changesets **nur** mit `runOnChange="true"` **oder** `runAlways="true"`.
  - **Nicht erlaubt**: Änderungen an bestehenden Changesets ohne diese Flags.

## 2. Ziel
- Automatisierte **PR-Prüfung** in GitHub Actions.
- Verletzungen führen zu **fehlgeschlagener Pipeline** (Exit-Code `1`).

## 3. Technischer Ansatz
- Eindeutige Identität eines Changesets: `(Dateipfad, id, author)`.
- Vergleich **Base-Branch vs. Head** (PR-Branch).
- Hash des Changeset-Inhalts (Canonical XML) zur Änderungserkennung.

## 4. Artefakte aus dieser Session
- **Python-CLI**-Script: `scripts/liquibase_guard.py`
- **Konfiguration**: `liquibase-guard.yml`
- **Whitelist** (optional): `liquibase-guard-exceptions.yml`
- **GitHub Action**: `.github/workflows/liquibase-guard.yml`
- **Beispielprojekt (ZIP)**: *siehe zuvor bereitgestellte Downloads*

## 5. Features der aktuellen Lösung
- ✅ **Diff-only**: Prüfung ausschließlich geänderter Dateien (per `git diff --name-only <base>...<head>`)
- ✅ **Pfad- und Extension-Filter** (z. B. nur `db/changelog/**/*.xml`)
- ✅ **Exception-Whitelist** über Globs für `file`, `id`, `author`
- ✅ **Mehrere Base-Branches** über Namensmuster (z. B. `main`, `release/*`, `hotfix/*`)
- ✅ **CI- und lokal** ausführbar

## 6. Konfiguration
### `liquibase-guard.yml`
```yaml
liquibase:
  changelogPaths:
    - db/changelog
  fileExtensions:
    - .xml
  baseBranchPatterns:
    - main
    - release/*
    - hotfix/*
  exceptionsFile: liquibase-guard-exceptions.yml
```

### Whitelist – `liquibase-guard-exceptions.yml`
```yaml
exceptions:
  - file: db/changelog/legacy/*.xml
    id: '*'
    author: '*'
  - file: db/changelog/002-add-column.xml
    id: add-name-column
    author: philipp
```

## 7. GitHub Action
`.github/workflows/liquibase-guard.yml`
```yaml
name: Liquibase Governance Check

on:
  pull_request:
    branches: [ '**' ]

jobs:
  liquibase-guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r scripts/requirements.txt
      - name: Governance check (diff only)
        env:
          GITHUB_BASE_REF: ${{ github.base_ref }}
        run: |
          git fetch --no-tags --prune origin "+refs/heads/*:refs/remotes/origin/*"
          python scripts/liquibase_guard.py \
            --config liquibase-guard.yml \
            --head HEAD
```

## 8. Unterstützung **mehrerer Base-Branches**
Die Base-Branch-Unterstützung erfolgt über `baseBranchPatterns` in der Config. Der Workflow nutzt automatisch `GITHUB_BASE_REF` (Zielbranch des PRs) und **führt den Check nur aus**, wenn der Branchname zu einem Pattern passt. Beispiele:

- `main` → prüft z. B. Feature-Branches, die gegen `main` mergen
- `release/*` → prüft PRs in Release-Zweige (z. B. `release/2026.01`)
- `hotfix/*` → prüft Hotfix-Backports

**Manuelles Überschreiben lokal:**
```bash
python scripts/liquibase_guard.py \
  --config liquibase-guard.yml \
  --head HEAD \
  --baseName release/2026.01
```

## 9. Skript-Verhalten (Kurzüberblick)
- Ermittelt geänderte relevante Dateien: `git diff --name-only origin/<base>...<head>`
- Lädt Datei-Inhalte aus Base- und Head-Ref via `git show <ref>:<path>` (kein Checkout nötig)
- Parst XML-Changesets, bildet Canonical-Hash je `changeSet`
- Wenn sich ein vorhandenes Changeset ändert, muss **`runOnChange` oder `runAlways`** gesetzt sein, sonst **Whitelist** erforderlich
- Verstöße werden gelistet; Exit-Code `1`

## 10. Nächste Schritte (optional)
- YAML-/JSON-Changesets zusätzlich unterstützen
- PR-Kommentar mit Detailergebnissen
- „Warn statt Fail“ für bestimmte Branches (Policy-Phasen)
- Java-CLI (Maven) identisch zur Python-Logik

---

*Stand: automatisch aus unserer Session generiert.*
