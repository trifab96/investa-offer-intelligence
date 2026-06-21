# Präsentations-Leitfaden — Investa Offer Intelligence

> Begleitnotizen für die beiden KI-Challenge-Präsentationen (§8 der Aufgabe).
> Als Skript + Argumentations-Referenz nutzen. Zeiten sind Richtwerte, keine Vorgaben.

> **Vollständige Folien-für-Folie-Decks mit Sprechernotizen + Q&A-Banken:**
> - Technisches Panel → [PRESENTATION_TECHNICAL.md](PRESENTATION_TECHNICAL.md)
>   (Herzhoff/CIO, Hesse, Cedric Quintes/anyon.studio, Vojinovic — Architektur, Technik/LLMs, Trade-offs)
> - Fachliches Panel → [PRESENTATION_BUSINESS.md](PRESENTATION_BUSINESS.md)
>   (Femerling/CEO, Vojinovic — Problem, Lösung, KI im Kontext, Alternativen; ~30 Min)
>
> Diese Datei ist der kompakte Überblick; aus den beiden Dateien oben sollte geprobt werden.

---

## 0. Pitch in einem Satz

> „Es verwandelt einen verrauschten, hochvolumigen Makler-Posteingang in eine **priorisierte
> Shortlist der wenigen Angebote, die einen genaueren Blick wert sind** — extrahiert die Fakten,
> erkennt Dubletten, reichert mit öffentlichen Daten an und erzeugt einen **transparenten,
> asset-klassen-bewussten 0–10-Score** samt Begründung.“

---

## 1. Live-Demo-Ablauf (funktioniert für beide Zielgruppen)

Stack laufen lassen (`docker compose up`) und die DB mit ein paar Objekten seeden, damit das Dedup
auslöst. **http://localhost:8080** öffnen.

1. **Home / Dashboard** — auf die Kennzahlen-Karten + das Score-Histogramm zeigen: *„Das ist die
   Portfolio-Sicht — ein Analyst sieht auf einen Blick, wie viele Angebote verfolgenswert sind.“*
2. **Geesthacht-`.msg` hochladen** — den Live-Status-Stepper kommentieren
   (`parsing → extracting → matching → enriching → scoring`).
3. **Ergebnis öffnen** und von oben nach unten durchgehen:
   - **Extrahierte Fakten** (100 % Confidence) — *„Das LLM extrahiert nur, es erfindet nie — fehlende
     Felder sind null.“*
   - **Karte + Anreicherung** — Geocoding, POIs, Bevölkerung, Miet-Benchmark — *„alles aus freien
     öffentlichen Quellen, jede gecacht und mit Zeitstempel.“*
   - **Score 6.96 / Einkommensobjekt** — die Sub-Scores aufklappen: *„beachten Sie Vermietungsstand
     und Reversion — dieses Angebot wird als Einkommensobjekt bewertet, nicht als generischer Block.“*
   - **Top-Treiber** — *„die drei Faktoren, die den Score am stärksten bewegt haben.“*
   - **Risiken/Chancen + Einschätzung** — die Urteils-Ebene des LLM.
   - **Bildanalyse** — *„das Vision-Modell hat das Luftbild aus dem PDF in der E-Mail gelesen.“*
   - **Prompt-Trace** — aufklappen: *„jeder LLM-Call ist wortwörtlich gespeichert — vollständig
     auditierbar.“*
   - **Originaldokument** — Seitenvorschau + Rohtext — *„volle Nachvollziehbarkeit zurück zur Quelle.“*
4. **Dasselbe Angebot erneut hochladen** → den Pfad **„Objekt bereits bekannt“** zeigen + den
   entworfenen Makler-Antwortbrief (keine Provision).
5. **Vergleichsseite** — 2–3 Angebote wählen → Radar-Chart.

**Backup, falls live scheitert:** Screenshots jedes Schritts; die API unter `/docs`; oder `GET /api/stats`.

---

## 2. Technische Präsentation (≈60 Min inkl. Q&A) — §8.1

### 2.1 Architektur (mit dem Diagramm in `docs/ARCHITECTURE.md` beginnen)
- **Drei Services, ein Befehl:** React (nginx) → FastAPI → PostgreSQL, via Docker Compose.
- **Pipeline** = Async-Background-Task mit **persistiertem Status**, den die UI pollt
  (`received → … → done|failed`). Ehrlicher Trade-off: kein Celery/Redis, aber die UX ist identisch
  und es ist ein Drop-in-Upgrade.
- **Provider-agnostischer LLM-Client** (OpenAI-kompatibel) → Default **GitHub Models** (kostenlos),
  austauschbar zu OpenAI/Azure/Gemini/Groq durch reines Editieren der `.env`. *Warum:* kein Lock-in,
  kein Lizenzproblem.

### 2.2 Prompt Engineering (`docs/PROMPTS.md` geöffnet halten)
- Prompts sind **versionierte Dateien** in `app/llm/prompts/`, nie Inline-Strings.
- **Drei fokussierte Prompts** (Extraktion / qualitatives Scoring / Antwort) statt eines Mega-Prompts.
- **Strukturierte JSON-Ausgabe** + Pydantic-Validierung; **`null` für Unbekanntes + Confidence** →
  Anti-Halluzination, entscheidend für einen Investment-Use-Case.
- **LLM ≠ Taschenrechner:** Code berechnet Rendite/€-m²/Distanzen; das LLM beurteilt nur Begehrtheit,
  Risiken, Einschätzung. Den Scoring-User-Prompt zeigen — er *bekommt* die Kennzahlen, soll nicht neu
  rechnen.
- **Nachvollziehbarkeit:** jeder Call persistiert als `{system, user, model, params, raw_response}` →
  im Prompt-Trace-Panel des UI sichtbar.

### 2.3 Datenintegration
- Freie/Key-lose Quellen: **Nominatim** (Geocoding, löst auch unvollständige Adressen), **Overpass**
  (POIs), **Wikidata** (Demografie), **mitgelieferter Mietspiegel-Seed** (dokumentierte Vereinfachung).
- **Jeder externe Call gecacht** in der DB mit `source` + `fetched_at`; **Pro-Host-Throttling +
  Retry/Backoff**; aussagekräftiger User-Agent (hart gelernt — OSM blockt Platzhalter-UAs).

### 2.4 Entscheidungslogik — der Differenzierer
- **Dedup:** Adresse normalisieren → `pg_trgm`-Vorfilter → RapidFuzz `token_sort_ratio` +
  Geo-Haversine; Schwellen konfigurierbar; Match-Evidenz gespeichert; Graubereich → `needs_review`.
- **Asset-klassen-bewusstes Scoring** (das Highlight): klassifizieren → Profil wählt Sub-Scores +
  Gewichte → hybride Mischung → Risiko-Abzug. Die drei Beispielangebote zeigen, die auf
  *unterschiedlichen* Kriterien bewertet werden (Grundstück auf Bebaubarkeit, Einkommensblock auf
  Vermietung/Reversion). Gewichte liegen in `scoring.yaml` → ohne Code tunebar.

### 2.5 Trade-offs & Alternativen (das Panel wird hier nachbohren)
| Entscheidung | Warum | Alternative / nächster Schritt |
|--------------|-------|--------------------------------|
| Async-Task vs. Queue | weniger bewegliche Teile für einen Prototyp | Celery/Redis oder RQ |
| Mietspiegel-Seed-CSV | keine freie Voll-API vorhanden | lizenzierter Daten-Feed / Scraper |
| Keyword-Asset-Klassifikator | deterministisch, günstig, transparent | kleiner LLM-Klassifikator mit Confidence |
| `create_all` vs. Migrationen | ok für 3-Tage-Prototyp | Alembic |
| Antwort entworfen, nicht versendet | laut Aufgabe out of scope | SMTP/Graph-Integration + menschliche Freigabe |

### 2.6 Im Entwicklungsprozess eingesetzte KI-Tools (§8.1 fordert das explizit)
- Gebaut mit einem KI-Coding-Agenten (GitHub Copilot) — im Pair-Programming-Stil.
- Bereit sein, den *Prozess* zu beschreiben: wie Prompts/Architektur iteriert wurden, wo die KI half
  (Boilerplate, Parsing-Edge-Cases) und wo **menschliches Urteil führte** (Scoring-Design,
  Asset-Klassen-Modell, Trade-offs). Die Aufgabe belohnt einen transparenten Entwicklungsprozess.

---

## 3. Fachliche Präsentation (≈30 Min inkl. Q&A) — §8.2

Ergebnisorientiert halten; Fachjargon vermeiden.

- **Das Problem in ihren Worten:** Makler fluten den Posteingang; die meisten Angebote sind bekannt,
  unattraktiv oder unvollständig; Fachkräfte verlieren Zeit mit der Triage.
- **Was das Tool tut:** *liest* das Angebot (E-Mail + PDF), *erkennt* Dubletten (und teilt es dem
  Makler höflich mit, keine Provision), *reichert* es mit Marktdaten an und *bewertet* es 0–10 mit
  klarer Empfehlung — **Verfolgen / Prüfen / Ablehnen**.
- **Warum der Score verlässlich ist:** die Sub-Scores, Top-Treiber und das „Bewertet als …“-Badge
  zeigen — *„es bewertet ein Baugrundstück anders als ein vermietetes MFH, wie ein Analyst.“*
- **Die Dubletten-Antwort:** konkreter Zeitgewinn + vermeidet Provisionsstreit.
- **Das Dashboard:** *„statt 30 PDFs zu lesen, schauen Sie auf die 3 grünen.“*
- **Ehrlichkeit zu Grenzen:** Entscheidungs-Unterstützung, kein Auto-Kauf; der Mensch bleibt im Loop;
  Datenquellen sind öffentlich/approximativ; der Mietspiegel ist ein Seed-Datensatz.

### Wahrscheinliche fachliche Fragen
- *„Kann es sich irren?“* → Ja; es zeigt Confidence, legt seine Begründung offen und markiert
  Angebote mit dünner Datenlage — darauf ausgelegt zu **priorisieren**, nicht zu entscheiden.
- *„Was ist mit Daten, die wir schon haben (SAP, SharePoint)?“* → Die Architektur ist API-first; die
  Bekannt-Objekt-Registry ist genau der Ort, an dem ein interner Feed andockt.
- *„Wie schnell / wie teuer?“* → Sekunden je Angebot; kostenlose LLM-Stufe + freie Datenquellen im
  Prototyp.

---

## 4. Zuordnung zu den Bewertungsdimensionen (§9)

| Dimension | Stärkster Beleg zum Zeigen |
|-----------|----------------------------|
| End-to-End-Vollständigkeit | volle Pipeline live auf echter `.msg` + PDF |
| KI-Kompetenz | strukturierte Ausgabe, LLM+Heuristik-Trennung, Vision, nachvollziehbare Prompts |
| Datenintegration | 4 externe Quellen, Caching, Throttling |
| **Fachliches Verständnis** | **asset-klassen-bewusstes Scoring + Reversion/Vermietung** |
| Systemdesign | Services, Status-Flow, konzeptionelle Skalierbarkeit, `scoring.yaml`-Tuning |
| Code & Umsetzung | saubere Module, Type Hints, Tests, `docs/` |
| Kommunikation | dieser Leitfaden / die beiden zugeschnittenen Vorträge |
| Entscheidungsfähigkeit | die Trade-off-Tabelle + klare „nächste Schritte“ |

---

## 5. „Hätte ich mehr Zeit“ (3 prägnante Antworten parat haben)
1. **Queue + Worker** (Celery/Redis) für Skalierung und Retries.
2. **Interne Datenintegration** (SAP/SharePoint) über das API-first-Design + ein echter Mietspiegel-Feed.
3. **LLM-Asset-Klassen-Klassifikator mit Confidence** + eine `needs_review`-Queue für unklare Angebote.
