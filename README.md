# Investa Offer Intelligence

> KI Challenge — Forward Deployed Engineer (AI / GenAI)

KI-gestützte Triage, Anreicherung und **0–10-Bewertung** eingehender Makler-Immobilienangebote
(E-Mail + PDF-Anhänge). Laden Sie ein Angebot hoch, und das System extrahiert die Kernfakten, prüft,
ob das Objekt **bereits bekannt** ist, reichert es mit **externen öffentlichen Daten** an und erzeugt
einen **nachvollziehbaren Attraktivitäts-Score** mit Risiken, Chancen und einer entscheidungsreifen
Zusammenfassung.

---

## Schnellstart

```bash
# 1) Umgebung konfigurieren
cp .env.example .env
#   dann .env bearbeiten und LLM_API_KEY setzen (ein GitHub-PAT mit "models"-Berechtigung;
#   GitHub Models ist der voreingestellte OpenAI-kompatible Provider — kostenlos + rate-limitiert)

# 2) Gesamten Stack bauen und starten
docker compose up --build

# 3) App öffnen
#    Frontend:  http://localhost:8080
#    API-Doku:  http://localhost:8000/docs
```

Optional — ein paar bekannte Objekte seeden, damit der Dubletten-Erkennungspfad sofort demonstriert
werden kann:

```bash
docker compose exec backend python -m scripts.seed_objects
```

Laden Sie dann ein Angebot für eine der geseedeten Adressen hoch (z. B. *Bürgerstraße 44, 12347
Berlin*), und das System erkennt es als **bereits bekannt** und entwirft eine Makler-Antwort mit dem
Hinweis, dass keine Provision anfällt.

---

## Was es tut (Zuordnung zur Aufgabenstellung)

| Aufgabe | Feature |
|---------|---------|
| 4.1 Ingestion | Web-Upload von `.msg`/`.eml` + Anhängen; PDF-Parsing (Textebene + **OCR-Fallback**); strukturierte Ausgabe |
| 4.2 Objekt-Erkennung **(Pflicht)** | Fuzzy-Adress-Matching (`pg_trgm` + RapidFuzz + Geo); persistente Registry bekannter Objekte; automatisch entworfene „bereits bekannt / keine Provision“-Antwort |
| 4.3 Persistenz | PostgreSQL speichert jedes Angebot, geparste Dokumente, Analyse, Anreicherungs-Snapshot und Antwort |
| 4.4 Analyse **(Kern)** | LLM-Extraktion (Typ, Lage, Größe, Preis, Zustand, Nutzung, Vermietungsstand) + **verpflichtende externe Anreicherung** (Geo, POIs, Demografie, Miet-Benchmark) + **Bildanalyse (Vision)** + Risiken/Chancen |
| 4.5 Scoring | **0–10 asset-klassen-bewusster Hybrid-Score** (Heuristik + LLM, Profile je Klasse + Risiko-Abzug), Kennzahlen, **Top-3-Treiber**, Sub-Score-Visualisierung, nachvollziehbare Begründung, Mehrfach-Angebotsvergleich |
| 5 Technik | LLM verpflichtend; **Prompts sind erstklassige, versionierte Dateien** mit vollständigen Traces; Docker Compose; persistente DB; kommentierte `.env.example` |
| Extras | Portfolio-**Dashboard** (Kennzahlen + Score-Histogramm), **Dokumentübersicht** (Seitenvorschau + extrahierter Text), **Karten**-Widget, Pro-Host-API-Throttling |

Siehe [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) für das vollständige Design,
[docs/PROMPTS.md](docs/PROMPTS.md) für den Prompt-Engineering-Katalog und
[docs/PRESENTATION_GUIDE.md](docs/PRESENTATION_GUIDE.md) für das Demo-Skript + die Argumentationspunkte.

---

## Architektur im Überblick

```
React + Vite + Tailwind  ──/api──▶  FastAPI  ──▶  Pipeline  ──▶  PostgreSQL (pg_trgm/PostGIS)
   (Upload + Dashboard)                │                          ▲
                                       ├─ ingestion (.msg/.eml/PDF/OCR)
                                       ├─ extraction (LLM, structured JSON)
                                       ├─ dedup (pg_trgm + RapidFuzz + geo)
                                       ├─ enrichment (Nominatim, Overpass, Wikidata, Mietspiegel seed)
                                       ├─ image analysis (Vision-LLM auf gerenderten Seiten)
                                       ├─ scoring (Asset-Klassen-Profile: Heuristik + LLM)
                                       └─ reply (LLM-Entwurf für bekannte Objekte)
                                                 │
                                       OpenAI-kompatibles LLM (Default: GitHub Models)
```

Pipeline-Status-Flow (persistiert; die UI pollt ihn):
`received → parsing → extracting → matching → enriching → scoring → done | failed`.

---

## LLM-Provider

Der gesamte LLM-Zugriff läuft über **einen OpenAI-kompatiblen Client**, sodass der Provider durch
reines Editieren der `.env` austauschbar ist:

- **Default: GitHub Models** — kostenlos, rate-limitiert, authentifiziert per GitHub-PAT
  (`models`-Berechtigung). Endpunkt `https://models.github.ai/inference`.
- **OpenAI / Azure OpenAI** — `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL` entsprechend setzen.

> Hinweis: Das In-Editor-Copilot-Abonnement wird **nicht** als Laufzeit-Backend der App genutzt (das
> würde seine Lizenz verletzen); GitHub Models ist der legitime, kostenlose Weg zu denselben Modellen.

**Prompt Engineering ist nachvollziehbar:** Jeder LLM-Call persistiert `{system, user, model, params,
raw_response, purpose}` auf der Analyse-Zeile (`analyses.prompt_trace`), und die UI legt den
vollständigen Trace hinter jeder Extraktion und jedem Score offen. Prompts liegen als versionierte
Dateien in `backend/app/llm/prompts/`.

---

## Persistenz

PostgreSQL (Image `postgis/postgis`, mit `pg_trgm` beim ersten Start via `backend/db/init/`
aktiviert). Tabellen: `offers`, `documents`, `objects`, `analyses`, `enrichments`, `replies`.
Daten liegen im Named Volume `pgdata`; Uploads im Volume `uploads`.

---

## Externe Datenquellen (verpflichtende Anreicherung)

| Quelle | Genutzt für | Auth |
|--------|-------------|------|
| Nominatim (OSM) | Geocoding + Auflösen unvollständiger Adressen | ohne Key |
| Overpass (OSM) | Mikrolage-POIs (ÖPNV, Schulen, Geschäfte…) | ohne Key |
| Wikidata | Gemeinde-Bevölkerung / Demografie | ohne Key |
| `mietspiegel_seed.csv` | Referenzmiete + Kaufpreis €/m² | mitgeliefert |

Jede externe Antwort wird **in der DB gecacht** mit `source` + `fetched_at` (Nachvollziehbarkeit +
Rate-Limit-Schonung). Es wird ein aussagekräftiger `User-Agent` gesendet (konfigurierbar).

---

## Lokale Entwicklung (ohne Docker)

Backend:

```bash
cd backend
pip install -e ".[dev,ocr]"
# DATABASE_URL auf ein lokales Postgres zeigen lassen, dann:
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxyt /api auf :8000)
```

Tests (reine Logik — keine DB/kein LLM nötig):

```bash
cd backend
pip install -e ".[dev]"   # installiert pytest
pytest

# …oder im laufenden Container:
# docker compose exec backend sh -c "pip install -q pytest pytest-asyncio && python -m pytest tests/ -q"
```

---

## Bewusste Vereinfachungen (gemäß Aufgabe §6)

| Vereinfachung | Warum sie sinnvoll ist |
|---------------|------------------------|
| Pipeline läuft als FastAPI-Background-Task (kein Celery/Redis) | Weniger bewegliche Teile für einen Prototyp; Status ist persistiert, die UX also identisch. Queue ist ein Drop-in-Upgrade. |
| Mietspiegel aus einer mitgelieferten Seed-CSV | Es existiert keine freie, umfassende Mietspiegel-API; eine kuratierte Tabelle je Region liefert realistische Benchmarks ohne Scraping. |
| Öffentliches Nominatim/Overpass (rate-limitiert) | Kostenlos + ohne Key; ausreichend für Prototyp-Volumina. Für Produktion self-hosten. |
| Demografie auf Gemeinde-Granularität | Wikidata ist auf dieser Ebene verlässlich; feinere Daten erfordern bezahlte Quellen. |
| Makler-Antwort wird **entworfen, nicht versendet** | Laut Aufgabe explizit out of scope (4.2). |
| `Base.metadata.create_all` statt Alembic | Vertretbar für einen 3-Tage-Prototyp; Migrationen sind der Produktionspfad. |

---

## Projektstruktur

```
.
├── docker-compose.yml          # postgres + backend + frontend
├── .env.example                # kommentierte Konfiguration
├── docs/
│   ├── ARCHITECTURE.md         # vollständiges Design + Diagramme
│   └── PROMPTS.md              # Prompt-Engineering-Katalog
├── backend/                    # FastAPI + Pipeline (Python 3.12)
│   ├── app/
│   │   ├── api/                # REST-Routen
│   │   ├── db/                 # Modelle + Session
│   │   ├── llm/                # OpenAI-kompatibler Client + prompts/
│   │   ├── pipeline/           # ingestion, extraction, dedup, enrichment, scoring, reply
│   │   └── schemas/            # Pydantic-Modelle
│   ├── data/mietspiegel_seed.csv
│   ├── scripts/seed_objects.py
│   └── tests/
└── frontend/                   # React + Vite + Tailwind Dashboard
```
