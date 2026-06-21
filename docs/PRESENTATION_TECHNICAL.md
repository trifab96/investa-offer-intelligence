# Technische Präsentation — Investa Offer Intelligence

> **KI Challenge — Forward Deployed Engineer (AI / GenAI)** · Bassem Trifa
> Publikum: Matthias Herzhoff (CIO), Christian Hesse, **Cedric Quintes (anyon.studio)**, Aleksandra Vojinovic
> Format: remote (MS Teams). Agenda: Architektur · Umsetzung (Technik/LLMs) · Entscheidungslogik & Trade-offs · Q&A
> Plan: **~25 Min Vortrag + ~20 Min Diskussion**. App laufen lassen + `docs/ARCHITECTURE.md` geöffnet halten.

---

## Anleitung zur Durchführung
- 12 Folien, ~2 Min je. Zahlen in **fett** sind echt, auf diesem Build gemessen — sie zitieren.
- Cedric (externes KI-Studio) treibt vermutlich die tiefe technische Q&A — die Folien zu
  **Prompt Engineering**, **hybridem Scoring** und **Trade-offs** entscheiden. Sie sitzen müssen.
- Herzhoff (CIO) interessiert **Betrieb, Skalierbarkeit, Integration, Kosten/Lizenz**. Das treffen.
- **Mit einer 3-Minuten-Live-Demo beginnen**, dann erklären, wie es funktioniert. Zeigen, dann erzählen.

---

## FOLIE 0 — Zuerst Live-Demo (3 Min)

**Tun, während des Erzählens:**
1. Home-Dashboard → *„Das ist der Endzustand: ein Posteingang als priorisierte Shortlist.“*
2. Die **Geesthacht-`.msg`** hochladen → den Live-Stepper kommentieren (`parsing → extracting →
   matching → enriching → scoring`).
3. Ergebnis von oben nach unten öffnen: Fakten (100 % Conf) → Karte + Anreicherung → **Score 6.96,
   „Einkommensobjekt“** → Top-Treiber → Risiken/Chancen → **Bildanalyse** → **Prompt-Trace** →
   **Originaldokument**.
4. Erneut hochladen → **„bereits bekannt“** + entworfene Makler-Antwort.

> Eröffnungssatz: *„Statt zuerst durch Folien zu gehen — lassen Sie mich das Ganze an einer echten
> Makler-E-Mail zeigen, Ende zu Ende, in etwa 20 Sekunden Verarbeitung.“*

**Backup, falls live scheitert:** Screenshots in diesem Ordner + `http://localhost:8000/docs`.

---

## FOLIE 1 — Problem & Framing (1 Min)

- Investa erhält einen konstanten Strom an Maklerangeboten (E-Mail + PDF). Die meisten sind **bereits
  bekannt, unwirtschaftlich oder unvollständig** — die manuelle Triage verbrennt Fachzeit.
- **Ziel:** eine automatisierte Triage, die extrahiert → Dubletten erkennt → anreichert → **0–10
  bewertet** mit transparenter Begründung, damit Analysten nur die wenigen Relevanten ansehen.
- **Mein Framing:** nicht „ein Angebot bewerten“, sondern **„den ganzen Posteingang triagieren“** —
  das hat das Dashboard- + Ranking-Design getrieben.

---

## FOLIE 2 — Architektur (3 Min) — *das Mermaid-Diagramm zeigen*

```
React (nginx) ──/api──▶ FastAPI ──▶ async pipeline ──▶ PostgreSQL (pg_trgm/PostGIS)
                                         │
   ingestion → extraction → dedup → enrichment → image analysis → scoring → reply
                                         │
                          OpenAI-kompatibles LLM (Default: GitHub Models) + freie öffentliche Daten-APIs
```

- **Drei Services, ein Befehl** (`docker compose up`): Frontend, Backend, DB. Healthchecks, Named
  Volumes für Persistenz.
- **Pipeline = Async-Background-Task** mit **persistiertem Status**, den das Frontend pollt
  (`received → … → done|failed`).
- **Provider-agnostischer LLM-Client** (OpenAI-kompatibel) — Default **GitHub Models** (kostenlos),
  austauschbar zu OpenAI/Azure/Gemini/Groq durch **3 Zeilen in der `.env`**, null Code-Änderung.

> Argument für Herzhoff: *„Kein Vendor-Lock-in und kein Lizenzproblem — das Copilot-Abo ist für die
> In-Editor-Nutzung; für die App habe ich GitHub Models genutzt, den legitimen, freien
> OpenAI-kompatiblen Weg, und die Abstraktion macht den Provider-Wechsel zur Konfigurationssache.“*

---

## FOLIE 3 — Die Pipeline, Stufe für Stufe (2 Min)

| Stufe | Was passiert | Technik |
|-------|--------------|---------|
| Ingestion | `.msg`/`.eml`/PDF/Bilder → Text; OCR-Fallback; **rendert eingebettete Anhänge** | extract-msg, pdfplumber, pypdfium2, tesseract |
| Extraktion | Text → strikte JSON-Fakten | LLM, structured output, Pydantic-validiert |
| Dedup | Bekannt-Objekt-Prüfung | pg_trgm + RapidFuzz + Geo-Haversine |
| Anreicherung | Geo, POIs, Demografie, Miet-Benchmark | Nominatim, Overpass, Wikidata, Seed-CSV |
| Bildanalyse | gerenderte Seiten → visuelle Hinweise | Vision-LLM |
| Scoring | asset-klassen-bewusst hybrid 0–10 | Heuristik + LLM |
| Antwort | „bereits bekannt / keine Provision“-Entwurf | LLM |

- Jedes Modul ist eine **weitgehend reine Funktion**, die Pydantic-Modelle nimmt/zurückgibt → testbar,
  komponierbar.

---

## FOLIE 4 — Prompt Engineering (3 Min) — *Cedrics Folie; `docs/PROMPTS.md` + einen Live-Prompt-Trace zeigen*

- **Prompts sind versionierte Dateien** in `app/llm/prompts/`, nie Inline-Strings.
- **Drei fokussierte Prompts** (Extraktion / qualitatives Scoring / Antwort) — Zerlegung statt eines
  Mega-Prompts.
- **Anti-Halluzination:** striktes JSON-Schema, **`null` für Unbekanntes + ein Confidence-Score**,
  niedrige Temperatur (0.1), Structured-Output-Modus. Entscheidend für einen Investment-Use-Case.
- **LLM ≠ Taschenrechner:** Code berechnet Rendite, €/m², Distanzen; der Scoring-Prompt *bekommt* die
  Kennzahlen und soll **nicht neu rechnen**. Das LLM macht nur das Urteil (Begehrtheit, Risiken,
  Einschätzung).
- **Volle Nachvollziehbarkeit:** jeder Call persistiert `{system, user, model, params, raw_response}`
  → im UI-Prompt-Trace-Panel sichtbar. *„Jede Zahl auf dem Bildschirm ist auf den exakten Prompt
  rückführbar.“*

> Wahrscheinliche Frage (Cedric): *„Wie verhinderst du halluzinierte Werte?“* → Schema + null +
> Confidence + niedrige Temperatur + das LLM sieht nie ein Feld, das es erfinden darf; fehlende Daten
> bleiben fehlend und senken die Confidence.

---

## FOLIE 5 — Entscheidungslogik 1: Dedup (2 Min)

- **Warum hybrid:** Adressen sind unsauber (`Bürgerstr.` vs. `Bürgerstraße 44`), kein Einzelverfahren
  reicht.
- **Pipeline:** normalisieren (Abkürzungen, Umlaute expandieren) → **pg_trgm**-Trigramm-Vorfilter
  (schnell, in SQL) → **RapidFuzz** `token_sort_ratio`-Feinabgleich → **Geo-Haversine**-Gate.
- **Entscheidung:** Match wenn `address_sim ≥ 0.88` **oder** (`≥ 0.75` und `< 150 m`); Graubereich →
  `needs_review`. Schwellen in der Konfiguration; **Match-Evidenz gespeichert**.
- **Demonstriert:** Re-Upload von Bürgerstraße / Bernau löst korrekt „bereits bekannt“ aus → entwirft
  die Makler-Antwort (keine Provision).

---

## FOLIE 6 — Entscheidungslogik 2: Asset-klassen-bewusstes Scoring (4 Min) — **der Differenzierer**

*Das ist die Folie, die einen Studenten von einem Engineer mit Domänenverständnis trennt. Hier Zeit nehmen.*

- **Der Fehler im naiven Design:** ein fixes Kriterienset ist für Immobilien falsch. Ein
  Entwicklungsgrundstück, ein vermietetes MFH und ein Büro werden auf **unterschiedlichen
  Fundamentaldaten** bewertet.
- **Lösung — Scoring-Profile:** Angebot klassifizieren → das Profil wählt, *welche* Sub-Scores gelten
  und ihre Gewichte.

| Asset-Klasse | Bewertet auf |
|--------------|--------------|
| Entwicklungsgrundstück | Bebaubarkeit (€/geplante Einheit), Lage, Größe/Nutzung |
| Einkommensobjekt (Wohnen) | Rendite, **Vermietung**, **Reversion**, Lage, Zustand |
| Gewerbeobjekt | Rendite, Vermietung, Lage, Zustand |

- **Hybrid + Risiko-Abzug:** heuristische Sub-Scores (harte Zahlen) gemischt mit dem LLM-Lageurteil;
  ein begrenzter **Risiko-Abzug** zieht für strukturelle Mängel ab (Altlast, Erbpacht, Leerstand…).
- **Top-3-Treiber** ausgewiesen („wichtigste Einflussfaktoren“).
- **Live-Beleg — dieselben drei Angebote, unterschiedliche Kriterien:**
  - Raintal-Höfe → **Entwicklungsgrundstück 6.45**, bewertet auf **Bebaubarkeit (111 Einheiten)**, −1.2 Genehmigungsrisiko
  - Geesthacht → **Einkommensobjekt 6.96**, Vermietung 9, **Reversion 2.0** (Miete bereits über Benchmark — eine echte Nuance)
  - CBRE → **Gewerbeobjekt 8.85**
- **Ohne Code tunebar:** Gewichte + Klassen liegen in `scoring.yaml`.

> Argument: *„Das beantwortet direkt die ‚Relevanz der gewählten Kriterien‘ aus der Aufgabe und passt
> zu Investas Multi-Asset-Realität — Büros, Hotels, Labore, Wohnen, Grundstücke.“*

---

## FOLIE 7 — Datenintegration & Resilienz (2 Min)

- Freie/Key-lose Quellen: **Nominatim** (Geocoding, löst unvollständige Adressen), **Overpass** (POIs),
  **Wikidata** (Demografie), mitgelieferter **Mietspiegel-Seed** (dokumentierte Vereinfachung).
- **Jeder externe Call gecacht** in der DB mit `source` + `fetched_at`.
- **Pro-Host-Throttling + Retry/Backoff**; aussagekräftiger User-Agent. *War-Story:* OSM liefert 403
  für Platzhalter-User-Agents — gefunden und behoben via Throttling + echtem UA. Zeigt Produktionsinstinkt.

---

## FOLIE 8 — Persistenz & Nachvollziehbarkeit (1 Min) — *das ER-Diagramm zeigen*

- PostgreSQL: `offers, documents, objects, analyses, enrichments, replies`.
- **`analyses.prompt_trace`** (JSONB) speichert jeden LLM-Call wortwörtlich → „Prompt Engineering muss
  nachvollziehbar sein“ auf der Datenebene erfüllt, nicht nur im UI.
- pg_trgm + PostGIS via Init-SQL beim ersten Start aktiviert.

---

## FOLIE 9 — Performance & Footprint (1 Min) — *echte gemessene Zahlen*

| Pfad | Zeit |
|------|------|
| Volle Neu-Objekt-Pipeline (3 LLM-Calls + 4 APIs + 4-Bild-Vision) | **~22 s** |
| Bekanntes Objekt (Dublette, Short-Circuit) | **~9 s** |
| Footprint im Leerlauf | Backend **487 MB** · postgres **87 MB** · frontend **9 MB** |

- Vision ist der größte Einzelposten (~11 s); es ist **optional** (`vision_enabled`-Flag).
- **Bekannter nächster Schritt:** Vision parallel zur Anreicherung laufen lassen (`asyncio.gather`) →
  ~20 % schneller.

---

## FOLIE 10 — Trade-offs & Alternativen (3 Min) — *Herzhoff + Cedric werden nachbohren; souverän vertreten*

| Entscheidung | Warum (pragmatisch) | Produktions-Nächstschritt |
|--------------|---------------------|---------------------------|
| Async-Task vs. Queue | weniger bewegliche Teile; Status persistiert → UX identisch | Celery/Redis oder RQ + Worker |
| Mietspiegel-Seed-CSV | keine freie Voll-API vorhanden | lizenzierter Feed (z. B. VALUE / on-geo) |
| Keyword-Asset-Klassifikator | deterministisch, transparent, günstig | kleiner LLM-Klassifikator mit Confidence |
| `create_all` vs. Migrationen | ok für 3-Tage-Prototyp | Alembic |
| Antwort entworfen, nicht versendet | laut Aufgabe out of scope | Graph/SMTP + menschliche Freigabe |
| Vision synchron | einfacher | parallelisieren + Bilder deckeln |

> Trade-offs als **bewusste Entscheidungen mit Nächstschritt** rahmen, nie als Lücken. Das ist eine
> explizite Bewertungsdimension („Begründung von Trade-offs“, „klarer Ausblick“).

---

## FOLIE 11 — KI-Tools im Entwicklungsprozess + Skalierung (2 Min)

- **Wie es gebaut wurde:** KI-Coding-Agent (GitHub Copilot) im Pair-Programming-Loop. Die KI
  beschleunigte Boilerplate, Parsing-Edge-Cases und Refactors; **menschliches Urteil trieb** das
  Scoring-Design, das Asset-Klassen-Modell und die Trade-offs. Die Aufgabe belohnt einen transparenten
  Entwicklungsprozess explizit — offen sein, wo die KI half und wo nicht.
- **Konzeptionelle Skalierung:** stateless API → horizontale Skalierung; Pipeline → Queue + Worker;
  externe Calls gecacht; provider-swappbares LLM; API-first-Design bereit zum Andocken an **SAP /
  SharePoint / internen Mietspiegel** (passt zum Integrationsfokus der Rolle).

---

## FOLIE 12 — Abschluss (30 s)

- *„Ende-zu-Ende, automatisiert, nachvollziehbar, asset-klassen-bewusst — in 3 Tagen gebaut, läuft mit
  einem Befehl und ist darauf ausgelegt, in Investas Datenlandschaft einzudocken.“*
- Fragen einladen.

---

## Q&A-Bank — technisch (prägnante Antworten parat haben)

**Architektur / Betrieb**
- *Warum keine Queue?* → Prototyp-Scope; Status ist persistiert, die UX also identisch; Celery/Redis
  ist ein Drop-in-Upgrade. Ich habe in 3 Tagen auf Klarheit optimiert.
- *Wie skaliert es?* → Stateless API skaliert horizontal; Pipeline → Worker; die DB ist der
  Bottleneck-Kandidat, konzeptionell mit Caching + Read-Replicas adressiert.
- *Kosten?* → Kostenlos: GitHub Models + freie öffentliche Datenquellen. ~22 s und ein paar LLM-Calls
  je Angebot.

**KI / LLM (Cedric)**
- *Halluzinations-Kontrolle?* → Schema + `null` + Confidence + niedrige Temperatur + Structured Output;
  das LLM rechnet nie Zahlen.
- *Warum GitHub Models?* → kostenlos, OpenAI-kompatibel, kein Lizenzproblem; die Abstraktion macht es
  austauschbar.
- *Wie ist Prompt Engineering nachvollziehbar?* → versionierte Prompt-Dateien + voller `prompt_trace`
  je Call, im UI sichtbar.
- *Warum LLM und Heuristik trennen?* → Determinismus + Auditierbarkeit für die Zahlen; LLM fürs Urteil.
  Das Beste aus beidem, und es ist die explizite Präferenz der Aufgabe.
- *Modellwahl?* → `gpt-4o-mini` für Extraktion/Scoring (günstig, schnell, gut bei Structured Output),
  `gpt-4o` für Vision. Austauschbar.

**Domäne / Scoring**
- *Wie validierst du den Score?* → Jeder Sub-Score hat Inputs + Begründung; Top-Treiber erklären ihn;
  Gewichte sind tunebar und transparent. Es ist Entscheidungs-Unterstützung, keine Ground Truth.
- *Was, wenn die Klassifikation falsch ist?* → `generic`-Fallback-Profil + die Klasse wird im UI
  gezeigt; ein LLM-Klassifikator mit Confidence ist der nächste Schritt.

**Daten**
- *Mietspiegel-Realismus?* → Ehrlich: ein kuratierter Seed, als Vereinfachung dokumentiert; Produktion
  tauscht über dieselbe Schnittstelle einen lizenzierten Feed ein.
- *Rate-Limits?* → Gecacht + gethrottelt + mit Retry; Nominatim/Overpass für Volumen self-hosten.

**Prozess**
- *Was würdest du mit mehr Zeit tun?* → (1) Queue + Worker, (2) interne Datenintegration
  (SAP/SharePoint) + echter Mietspiegel, (3) LLM-Klassifikator + eine `needs_review`-Queue.
