# Prompt-Engineering-Katalog

Dieses Dokument macht das Prompt Engineering **nachvollziehbar**.
Jeder LLM-Call im System ist:

1. in einer **versionierten Template-Datei** unter `backend/app/llm/prompts/` definiert (niemals ein
   inline zusammengebauter Ad-hoc-String) und
2. **vollständig persistiert** als Trace `{system, user, model, params, raw_response, purpose}` in der
   Spalte `analyses.prompt_trace` — und im UI sichtbar (Panel „Prompt-Trace“ je Angebot).

## Angewandte Designprinzipien

| Technik | Wie / wo |
|---------|----------|
| **Strukturierte (JSON-)Ausgabe** | Extraktion und qualitatives Scoring nutzen `response_format={"type":"json_object"}` und werden gegen Pydantic-Schemata validiert (`Extraction`, `Scoring`). |
| **Anti-Halluzination / Grounding** | Der Extraktions-System-Prompt verbietet das Erfinden von Werten explizit: Unbekanntes → `null`, plus ein `confidence`-Score. Entscheidend für einen Investment-Use-Case. |
| **LLM ≠ Taschenrechner** | Der Scoring-Prompt soll *keine* Kennzahlen rechnen. Rendite, €/m², POI-Zählungen etc. werden im Code berechnet (`pipeline/scoring.py`); das LLM beurteilt nur Begehrtheit, Risiken und Chancen. |
| **Aufgaben-Zerlegung** | Drei fokussierte Prompts (Extraktion, Scoring, Antwort) statt eines Mega-Prompts — jeder kleiner, testbar und wiederverwendbar. |
| **Determinismus** | Niedrige Temperatur (`LLM_TEMPERATURE=0.1`) für Extraktion & Scoring; leicht höher (0.3) für die Antwort, wo natürliche Formulierung hilft. |
| **Schema im Prompt** | Die exakte JSON-Form ist im Extraktions-System-Prompt eingebettet, damit das Modell beim ersten Versuch parsebare Ausgabe liefert. |
| **Domänen- + Sprach-Framing** | Alle Prompts sind auf Deutsch und rahmen das Modell als Immobilien-Analyst bei einem institutionellen Investor — passend zu den Quelldokumenten und dem Geschäftskontext. |
| **Robustes Scheitern** | Der Client liefert immer einen Trace, auch im Fehlerfall (`raw_response` = `ERROR: …`); die Validierung fällt auf ein leeres Ergebnis mit niedriger Confidence zurück, statt die Pipeline abstürzen zu lassen. |

## Die Prompts

### 1. Extraktion — `extraction_system.txt` + `extraction_user.txt`
- **Zweck:** Roh-Angebotstext (E-Mail-Body + geparste Anhänge) in strikte, strukturierte Fakten überführen.
- **Kernanweisungen:** niemals erfinden; `null` für Unbekanntes; nicht rechnen/runden; nur JSON
  zurückgeben; eine `confidence` in `[0,1]` ausgeben.
- **Ausgabe:** validiert gegen das `Extraction`-Schema (`backend/app/schemas/models.py`).

### 2. Qualitatives Scoring — `scoring_system.txt` + `scoring_user.txt`
- **Zweck:** die *Urteils*-Hälfte des hybriden Scores — Lagebegehrtheit, Risiken, Chancen und eine
  kurze Einschätzung für den Analysten.
- **Bereitgestellte Inputs:** die extrahierten Fakten, das externe Anreicherungs-Bundle **und die
  bereits berechneten Kennzahlen** (damit das Modell keine Zahlen neu herleitet).
- **Ausgabe:** `location_desirability`, `location_rationale`, `risks[]`, `opportunities[]`,
  `narrative`. Im Code mit den heuristischen Sub-Scores gemischt.

### 3. Makler-Antwort (bekanntes Objekt) — `reply_known_system.txt` + `reply_known_user.txt`
- **Zweck:** eine höfliche deutsche Antwort entwerfen, die darauf hinweist, dass das Objekt bereits
  bekannt ist und keine Provision anfällt. Die Antwort wird **entworfen, nicht versendet**.
- **Ausgabe:** Freitext-E-Mail, im UI angezeigt.

## So inspiziert man einen Trace

1. Im UI ein Angebot hochladen und dessen Detailseite öffnen.
2. Unten **„Prompt-Trace“** aufklappen — jeder Call zeigt seinen System-Prompt, die exakte
   User-Nachricht (inkl. eingefügter Daten), das Modell + Parameter und die Roh-Antwort.
3. Dieselben Daten gibt es über die API: `GET /api/offers/{id}` → `prompt_trace`.

## Hybrides Scoring: welcher Teil ist LLM vs. Heuristik

| Sub-Score | Quelle |
|-----------|--------|
| `price_vs_market` | **Heuristik** — Bruttorendite oder €/m² vs. regionaler Benchmark |
| `condition` | **Heuristik** — Keyword-Tabelle in `scoring.yaml` |
| `size_usage` | **Heuristik** — Nutzungsoptionen + Einheiten |
| `data_completeness` | **Heuristik** — Anteil vorhandener Schlüsselfelder |
| `location` | **Mischung** — POI-Dichte (Heuristik) + LLM-Begehrtheit |
| narrative / risks / opportunities | **LLM** |

Endscore = gewichtete Mischung (Gewichte in `.env` / `scoring.yaml`), auf 0–10 begrenzt. Jeder
Sub-Score speichert seine numerischen Inputs und eine Begründung, sodass jeder Score vollständig
auditierbar ist.

> Hinweis zum asset-klassen-bewussten Scoring: Welche Sub-Scores tatsächlich angewandt werden und mit
> welchen Gewichten, hängt von der erkannten Asset-Klasse ab (Profile in `scoring.yaml`). Details in
> [ARCHITECTURE.md](ARCHITECTURE.md) §3.5.
