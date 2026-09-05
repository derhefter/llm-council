# Tests

```bash
uv sync --group dev
uv run pytest
```

The council's only external dependency is OpenRouter. `conftest.py` replaces
that single call with a stub that answers by prompt type, so the whole suite
runs offline, deterministically and without an API key — and CI needs no secret.

| Datei | Deckt ab |
|---|---|
| `test_prompts.py` | Kontext-Assembly, Trunkierung, Anonymisierung in Stage 2, Rubrik und Output-Schema je Profil |
| `test_ranking.py` | Parser für `FINAL RANKING:` inklusive kaputter Ausgaben, Aggregation, Gleichstand |
| `test_run.py` | Alle drei Stages, `quick` ohne Peer-Review, Ausfall einzelner Modelle, Kosten-/Token-Summen, Persistenz |
| `test_cli.py` | Exit-Codes, Report-Aufbau, `--file` / `--out` / `--json` / `--adr` |
| `test_api.py` | Beide Endpoints, Streaming-Eventfolge, Profil-Durchreichung, Metadaten nach Reload |
| `test_export.py` | ADR-Nummerierung, Frontmatter, Ranking-Tabelle |
| `test_mcp.py` | `council_start` / `_result` / `_ask` / `_profiles` / `_write_adr` |

## Was hier bewusst nicht getestet wird

Der echte OpenRouter-Aufruf. Ob eine Modell-ID in `backend/config.py` noch
existiert und ob der Schlüssel gilt, klärt nur ein echter Lauf — siehe
`ANLEITUNG-KONZIL.md`. Die Tests beweisen die Mechanik, nicht die Anbindung.
