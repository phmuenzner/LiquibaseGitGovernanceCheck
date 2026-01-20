
# Liquibase Guard Example (Advanced)

Governance-Check für Liquibase-Changesets in GitHub Pull Requests.

**Features**
- Prüfung **nur der geänderten Dateien** (`git diff`)
- **Exception-Whitelist** (glob-Matching auf file/id/author)
- **Mehrere Base-Branches** per Namenspattern (z. B. `main`, `release/*`, `hotfix/*`)
- Pfad-/Extension-Filter (konfigurierbar)
- CI- und lokal ausführbar

## Schnelleinstieg (lokal)

```bash
pip install -r scripts/requirements.txt
# Prüft aktuellen HEAD gegen origin/<baseBranch>, ermittelt aus GITHUB_BASE_REF oder --baseName
python scripts/liquibase_guard.py --config liquibase-guard.yml --head HEAD --baseName main
```

## In GitHub Actions
Workflow liegt unter `.github/workflows/liquibase-guard.yml` und nutzt `GITHUB_BASE_REF`.

## Regeln
- Neue Changesets sind erlaubt
- Änderungen an bestehenden Changesets nur erlaubt, wenn `runOnChange="true"` **oder** `runAlways="true"`
- Sonst: Fehler (Exit-Code 1)
- Ausnahmen können über `liquibase-guard-exceptions.yml` gepflegt werden

## Konfiguration
Siehe `liquibase-guard.yml`.
