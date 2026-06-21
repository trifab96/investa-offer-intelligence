# Investa Offer Intelligence — Architektur & Konzept

> KI Challenge — Forward Deployed Engineer (AI / GenAI)
> KI-gestützte Triage, Anreicherung und Bewertung eingehender Makler-Immobilienangebote.

---

## 1. Problem & Ziel

Investa Real Estate erhält laufend unaufgeforderte Maklerangebote (E-Mail + PDF-Anhänge) zu
Immobilien und Grundstücken. Der Eingang ist hochvolumig und heterogen: Viele Angebote sind
**bereits bekannt**, **wirtschaftlich unattraktiv** oder **unvollständig / schwer vergleichbar**.
Die manuelle Prüfung ist langsam und bindet Fachressourcen.

**Ziel:** ein End-to-End-Prototyp, der ein Angebot einliest, die Kernfakten extrahiert, prüft ob das
Objekt bereits bekannt ist, es mit externen öffentlichen Daten anreichert und einen
**nachvollziehbaren 0–10-Attraktivitäts-Score** plus eine entscheidungsreife Zusammenfassung erzeugt
— damit Analysten nur noch Zeit in die wenigen relevanten Angebote investieren.

### Erfolgskriterien

| # | Anforderung | Wo umgesetzt |
|---|-------------|--------------|
| 4.1 | Web-Upload von E-Mail + Anhängen, Parsing (inkl. PDF), Strukturierung | Frontend + `ingestion`-Service |
| 4.2 | Bekannt-Objekt-Erkennung via Fuzzy-Matching + Persistenz + Makler-Antwortentwurf | `dedup`-Modul + `objects`-Tabelle + `reply`-Generator |
| 4.3 | Persistente Speicherung bekannter Objekte + jedes verarbeiteten Angebots & seiner Analyse | PostgreSQL-Schema |
| 4.4 | Extraktion + externe Anreicherung (+ Vision/Risiko) | `extraction`- + `enrichment`-Module |
| 4.5 | 0–10-Bewertung mit Kennzahlen, Visualisierung, nachvollziehbarer Begründung | `scoring`-Modul + Dashboard |
| 5 | LLM-Integration, nachvollziehbare Prompts, LLM+Heuristik, Docker Compose, DB, README, `.env.example` | gesamtes Repo |
| 6 | Weitgehend automatisiert; dokumentierte Vereinfachungen | Pipeline + README-Abschnitt „Vereinfachungen“ |

### Umfang

Alle Kern-Anforderungen (4.1–4.6, 5, 6) sind umgesetzt und Ende-zu-Ende auf den echten
Beispielangeboten verifiziert (2 PDFs + 2 Outlook-`.msg` mit eingebetteten Anhängen). Darüber
hinaus sind diese zusätzlichen Features gebaut:

- **Asset-klassen-bewusstes Scoring** mit Profilen je Klasse + Risiko-Abzug (§3.5)
- **Bildanalyse (4.4c)** — Vision-Modell liest gerenderte PDF-Seiten / Fotos, inkl. Anhängen in einer `.msg`
- **Geolokalisierung aus unvollständigen Adressen** (Nominatim-Freitext + `lagebeschreibung`-Fallback)
- **Top-3-Score-Treiber** („wichtigste Einflussfaktoren“)
- **Dokumentübersicht** — Original-Seitenvorschau + extrahierter Text je Dokument (Nachvollziehbarkeit)
- **Portfolio-Dashboard** — Kennzahlen, Score-Histogramm, Top-Angebote (Triage auf Posteingangsebene)
- **Karten-Widget**, **Mehrfach-Angebotsvergleich**, **Pro-Host-API-Throttling + Retry/Backoff**

---

## 2. Architektur im Überblick

```mermaid
flowchart LR
    subgraph Client
        UI[React + Vite + Tailwind\nUpload + Dashboard]
    end

    subgraph API[FastAPI Backend]
        REST[REST API]
        PIPE[Async Processing Pipeline]
    end

    subgraph Workers[Processing modules]
        ING[Ingestion\n.msg / .eml / PDF / images]
        EXT[LLM Extraction]
        DED[Dedup / Object Recognition\nfuzzy + geo]
        ENR[External Enrichment]
        SCO[Scoring\nLLM + heuristics]
        REP[Broker Reply Draft]
    end

    subgraph Data
        PG[(PostgreSQL\n+ pg_trgm / PostGIS)]
        FS[(Upload volume\nraw files)]
    end

    subgraph External[Free external APIs]
        NOM[Nominatim / OSM geocode]
        OVP[Overpass POIs/transit]
        WIKI[Wikidata / Wikipedia\ndemographics, economy]
        MIET[(Seed Mietspiegel dataset)]
    end

    subgraph LLM[LLM Provider]
        GH[GitHub Models\nOpenAI-compatible]
    end

    UI -->|upload| REST
    UI -->|poll status / results| REST
    REST --> PIPE
    PIPE --> ING --> EXT --> DED --> ENR --> SCO --> REP
    EXT <-->|prompts| GH
    SCO <-->|prompts| GH
    ENR --> NOM & OVP & WIKI & MIET
    ING --> FS
    PIPE --> PG
    DED --> PG
```

### Verantwortlichkeiten der Komponenten

- **Frontend (React + Vite + Tailwind):** Drag-&-Drop-Upload von `.msg`/`.eml` + Anhängen;
  Angebotsliste; Detailansicht mit extrahierten Feldern, Anreicherungs-Karten, Score-Gauge,
  Risiken/Chancen, generiertem Makler-Antwortentwurf und einem Mehrfach-Vergleich. Charts via Recharts.
- **API (FastAPI):** REST-Endpunkte, Request-Validierung (Pydantic), stößt die asynchrone Pipeline an,
  stellt Status + Ergebnisse bereit. OpenAPI-Doku automatisch unter `/docs`.
- **Pipeline:** orchestriert die folgenden Module. Im Prototyp läuft sie als asynchroner
  Background-Task mit persistiertem `status` je Angebot (`received → parsing → extracting → matching →
  enriching → scoring → done/failed`), den die UI pollt. (Eine Redis/RQ-Queue ist ein leichter
  späterer Ausbau — siehe §9.)
- **PostgreSQL:** Single Source of Truth für Angebote, bekannte Objekte, Analysen,
  Anreicherungs-Snapshots und generierte Antworten. `pg_trgm` für Trigramm-Fuzzy-Matching; PostGIS
  (optional) für Geo-Distanz.

---

## 3. Verarbeitungs-Pipeline (je Angebot)

```mermaid
sequenceDiagram
    participant UI
    participant API
    participant ING as Ingestion
    participant EXT as Extraction(LLM)
    participant DED as Dedup
    participant ENR as Enrichment
    participant SCO as Scoring
    participant DB as PostgreSQL

    UI->>API: POST /offers (email + attachments)
    API->>DB: insert offer (status=received)
    API-->>UI: 202 {offer_id}
    API->>ING: parse files
    ING->>DB: store raw text + attachment meta (status=parsing)
    ING->>EXT: combined text (+ images)
    EXT->>DB: structured fields JSON (status=extracting)
    EXT->>DED: normalized address + geo seed
    DED->>DB: match? known_object_id / new (status=matching)
    alt Object known
        DED->>SCO: short-circuit (reuse prior analysis)
        SCO->>DB: reply draft "already known, no commission"
    else New object
        DED->>ENR: geocode + enrich (status=enriching)
        ENR->>DB: enrichment snapshot
        ENR->>SCO: features
        SCO->>DB: score + rationale + risks (status=scoring)
    end
    DB-->>UI: status=done + results (poll)
```

### 3.1 Ingestion (4.1)
- `.msg` → `extract-msg`; `.eml` → stdlib `email`. Betreff, Body, Absender, Anhänge auslesen.
- PDF → `pdfplumber` (Text) mit `pypdf`-Fallback; **OCR-Fallback** via `pytesseract` für gescannte PDFs.
- Bilder (jpg/png) werden für die optionale Vision-Analyse aufbewahrt.
- Ausgabe: normalisierte `documents[]` (Typ, Dateiname, extrahierter Text) + zusammengeführter Korpus.

### 3.2 LLM-Extraktion (4.4a)
Ein einzelner Structured-Output-Call liefert striktes JSON (validiert per Pydantic-Schema):
`objektart, lage{strasse, plz, ort, bundesland, lagebeschreibung}, groesse{grundstueck_m2,
wohnflaeche_m2, einheiten}, kaufpreis{betrag, waehrung, basis}, zustand, nutzungsmoeglichkeiten[],
miete_ist, miete_soll, baujahr, confidence`. Fehlende Werte → `null` (niemals halluziniert).
Nutzt den „JSON / structured output“-Modus des Providers; Prompt + Roh-Antwort werden zur
Nachvollziehbarkeit persistiert.

### 3.3 Dedup / Objekt-Erkennung (4.2)
Hybrides, erklärbares Matching:
1. **Normalisieren** der Adresse (Kleinschreibung, `str.→strasse` expandieren, Interpunktion entfernen, PLZ/Ort parsen).
2. **Kandidaten laden** aus `objects` via `pg_trgm`-Ähnlichkeit auf `address_norm` (schneller Vorfilter).
3. **Bewerten** jedes Kandidaten mit `RapidFuzz` (`token_sort_ratio` auf Adresse + Name) **und**
   Geo-Distanz (Haversine auf geokodierten lat/lon).
4. **Entscheidung:** `Match wenn address_sim ≥ 0.88 ODER (address_sim ≥ 0.75 UND geo_distance < 150 m)`
   (Schwellen konfigurierbar). Graubereich → als `needs_review` markiert.
5. Bei Treffer → Angebot mit bestehendem Objekt verknüpfen, **Makler-Antwort generieren** (Objekt
   bereits bekannt → keine Provision), Anreicherung/Scoring überspringen (vorhandene Analyse nutzen).
6. Bei neuem Objekt → kanonisches `object` anlegen, Pipeline fortsetzen.

### 3.4 Externe Anreicherung (4.4b)
Wo möglich kostenlos / ohne Key; jeder Call in der DB mit Zeitstempel + Quelle gecacht
(Nachvollziehbarkeit).

| Signal | Quelle | Hinweise |
|--------|--------|----------|
| Geocoding (lat/lon, kanonische Adresse) | **Nominatim** (OSM) | behebt auch unvollständige Adressen (4.4c) |
| Mikrolage-POIs, ÖPNV, Schulen | **Overpass API** (OSM) | Zählungen im Radius |
| Demografie, Bevölkerung, Wirtschaft | **Wikidata / Wikipedia REST** | Fakten auf Gemeindeebene |
| Lokale Miete / Mietspiegel | **Seed-CSV-Datensatz** (mitgeliefert) | dokumentierte Vereinfachung (§9); Schlüssel PLZ/Ort |
| Makro-Indikatoren (optional) | Destatis Regionaldatenbank | falls Zeit |

Anreicherungs-Ausgabe: ein strukturierter `enrichment`-JSON-Snapshot (je Quelle), der den Scorer speist.

### 3.5 Scoring (4.5) — asset-klassen-bewusst, hybrid (LLM + Heuristik)

Das Scoring ist bewusst **hybrid, transparent und asset-klassen-bewusst**. Ein einziges fixes
Kriterienset ist für Immobilien falsch: Ein Entwicklungsgrundstück, ein vermietetes Mehrfamilienhaus
und ein Büro werden auf *unterschiedlichen* Fundamentaldaten bewertet. Daher **klassifiziert** der
Scorer zuerst das Angebot und wendet dann ein passendes **Scoring-Profil** an, das bestimmt, *welche*
Sub-Scores gelten und mit welchen Gewichten.

```mermaid
flowchart LR
    EX[Extraction + enrichment<br/>+ computed metrics] --> CL{classify_asset}
    CL -->|development_land| P1[buildability · location<br/>· size_usage · condition]
    CL -->|income_residential| P2[price · occupancy · reversion<br/>· location · condition]
    CL -->|commercial| P3[price · occupancy<br/>· location · condition]
    CL -->|generic fallback| P4[location · price<br/>· condition · size · completeness]
    P1 & P2 & P3 & P4 --> BLEND[weighted blend] --> RP[− risk penalty] --> S[Score 0–10]
```

**1. Klassifikation.** `classify_asset()` ordnet das Angebot einer von `development_land`,
`income_residential`, `commercial` oder einem `generic`-Fallback zu — per Keyword-Regeln über
`objektart` + `nutzungsmöglichkeiten` (Konfiguration in `scoring.yaml`; Entwicklungsgrundstück hat
Vorrang, weil ein Grundstück auch „Wohnen“ erwähnen kann). Die gewählte Klasse + Label werden
gespeichert und im UI gezeigt („Bewertet als: Einkommensobjekt“).

**2. Heuristische Sub-Scores (0–10), im Code aus harten Zahlen berechnet** — nur die, die das Profil listet:
- `price_vs_market` — Bruttorendite (Miete ÷ Preis) oder €/m² vs. regionaler Benchmark
- `occupancy` — Vermietungsstand (die zentrale Risiko-Kennzahl eines Einkommensobjekts)
- `reversion` — Mietsteigerungspotenzial: aktuelle vs. potenzielle/Benchmark-Miete (untervermietet = Upside)
- `buildability` — bei Grundstücken: geplante Einheiten und Preis je bebaubarer Einheit
- `location` — POI-/ÖPNV-Dichte + Demografie (mit dem LLM-Urteil zur Begehrtheit gemischt)
- `condition`, `size_usage`, `data_completeness`

**3. Qualitative LLM-Ebene.** Das Modell bewertet die Lagebegehrtheit, leitet Risiken & Chancen ab und
schreibt eine menschenlesbare Einschätzung — auf Basis der extrahierten Fakten, der Anreicherung und
der **bereits berechneten Kennzahlen** (es leitet niemals Zahlen neu her).

**4. Risiko-Abzug.** Die Risiko-Liste des LLM wird in einen begrenzten Score-Abzug übersetzt (schwere
Stichworte — `altlast`, `erbpacht`, `leerstand`, … — zählen doppelt, gedeckelt). Das verhindert, dass
eine hohe Rendite bei strukturell mangelhaftem Asset durchrutscht, und erscheint als negativer
„Top-Treiber“.

**5. Endscore** = profilgewichtete Mischung (Gewichte je Profil normalisiert), minus Risiko-Abzug,
auf 0–10 begrenzt. Jede Komponente — ihr Wert, Gewicht, Inputs, Begründung, das gewählte Profil, der
Prompt und die Roh-LLM-Antwort — wird persistiert, sodass die Zahl vollständig **auditierbar** ist.

**6. Top-Treiber (4.5 „wichtigste Einflussfaktoren“).** Sub-Scores werden nach vorzeichenbehafteter
gewichteter Abweichung vom neutralen Mittel (5.0) gerankt; die Top 3 (inkl. Risiko-Abzug) werden als
die zentralen Faktoren ausgewiesen, die den Score bewegen.

- Ausgabe: `score`, `band` (0–3 reject / 4–6 review / 7–10 pursue), `asset_class(_label)`,
  `subscores[]`, `top_drivers[]`, `risk_penalty`, `rationale`, `risks[]`, `opportunities[]`.

> **Warum dieses Design.** Es adressiert direkt die Relevanz der gewählten Kriterien und passt zu Investas Multi-Asset-Realität (Büros, Hotels, Labore, Wohnen,
> Grundstücke). Profile liegen in `scoring.yaml`, sodass ein Analyst Gewichte nachjustieren oder eine
> Asset-Klasse ergänzen kann **ohne Code anzufassen** — Heuristiken bleiben deterministisch, das LLM
> bleibt auf das Urteil beschränkt, nie auf Arithmetik.

### 3.6 Makler-Antwort (4.2)
LLM-generierte deutsche E-Mail-Antwort für bekannte Objekte: höflich, weist darauf hin, dass das
Objekt bereits bekannt ist und keine Provision anfällt. Gespeichert, im UI angezeigt — **nicht
versendet**.

---

## 4. Datenmodell (PostgreSQL)

```mermaid
erDiagram
    OFFERS ||--o{ DOCUMENTS : has
    OFFERS ||--o| ANALYSES : produces
    OFFERS }o--o| OBJECTS : references
    OBJECTS ||--o{ ENRICHMENTS : cached
    OFFERS ||--o{ REPLIES : drafts

    OFFERS {
        uuid id PK
        text source_email
        text subject
        text sender
        text raw_text
        text status
        timestamptz created_at
    }
    DOCUMENTS {
        uuid id PK
        uuid offer_id FK
        text filename
        text doc_type
        text extracted_text
        text storage_path
    }
    OBJECTS {
        uuid id PK
        text address_raw
        text address_norm
        text plz
        text ort
        double lat
        double lon
        text dedup_key
        timestamptz first_seen
    }
    ANALYSES {
        uuid id PK
        uuid offer_id FK
        jsonb extraction
        jsonb enrichment
        jsonb scoring
        numeric score
        text band
        text llm_model
        jsonb prompt_trace
        timestamptz created_at
    }
    ENRICHMENTS {
        uuid id PK
        uuid object_id FK
        text source
        jsonb payload
        timestamptz fetched_at
    }
    REPLIES {
        uuid id PK
        uuid offer_id FK
        text language
        text body
        text reason
        timestamptz created_at
    }
```

`prompt_trace` hält `{system, user, model, params, raw_response}` für jeden LLM-Call → erfüllt
„Prompt Engineering muss nachvollziehbar sein“.

---

## 5. API-Oberfläche (FastAPI)

| Methode | Pfad | Zweck |
|---------|------|-------|
| `POST` | `/api/offers` | E-Mail + Anhänge hochladen → liefert `offer_id`, startet Pipeline |
| `GET` | `/api/offers` | Angebote auflisten (Status, Score, Objekt, created_at) |
| `GET` | `/api/offers/{id}` | Vollergebnis: Extraktion, Anreicherung, Score, Begründung, Antwort, Dokumenttext |
| `GET` | `/api/offers/{id}/status` | Schlanker Status fürs Polling |
| `GET` | `/api/offers/{id}/preview` | Rendert Original-PDF-Seiten / Bilder bei Bedarf zu Thumbnails |
| `GET` | `/api/objects` | Registry bekannter Objekte |
| `GET` | `/api/compare?ids=...` | Vergleichs-Payload nebeneinander |
| `GET` | `/api/stats` | Portfolio-Kennzahlen (Summen, Ø-Score, Band-Zählungen, Histogramm, Top-Angebote) |
| `GET` | `/api/health` | Liveness für den Docker-Healthcheck |

---

## 6. Frontend (React + Vite + Tailwind)

- **Upload-Seite:** Drag-&-Drop, zeigt den Live-Pipeline-Status (Stepper).
- **Angebotsliste:** sortierbare Tabelle — Score-Badge, Band-Farbe, Objekt, Datum, „bekannt“-Flag.
- **Angebots-Detail:** Karte mit extrahierten Feldern, Anreicherungs-Karten (Kartenmarker, Demografie,
  Miet-Benchmark, POIs), **Score-Gauge** + Sub-Score-Balken, Risiken/Chancen, Makler-Antwort-Panel.
- **Vergleichsansicht:** 2–4 Angebote wählen → Tabelle + Radar-Chart der Sub-Scores.
- Charts: Recharts. State/Daten: TanStack Query gegen die REST-API.

---

## 7. Repository-Struktur

```
.
├── README.md                     # Ausführungsanleitung (Root)
├── docker-compose.yml            # frontend + backend + postgres (+ optional ocr)
├── .env.example                  # kommentiert, alle Konfig-Schlüssel
├── docs/
│   └── ARCHITECTURE.md           # dieses Dokument
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py               # FastAPI-App + Routen
│   │   ├── config.py             # Einstellungen (pydantic-settings)
│   │   ├── db/                   # Modelle, Session, Migrationen
│   │   ├── pipeline/
│   │   │   ├── ingestion.py
│   │   │   ├── extraction.py
│   │   │   ├── dedup.py
│   │   │   ├── enrichment/       # nominatim.py, overpass.py, wiki.py, mietspiegel.py
│   │   │   ├── scoring.py
│   │   │   └── reply.py
│   │   ├── llm/                  # provider-agnostischer OpenAI-kompatibler Client + Prompts
│   │   └── schemas/              # Pydantic-Modelle
│   ├── data/
│   │   └── mietspiegel_seed.csv  # mitgelieferter Fallback-Datensatz
│   └── tests/
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/                      # Seiten, Komponenten, API-Client
```

---

## 8. Konfiguration & LLM-Abstraktion

`.env.example` (kommentiert) steuert alles. Der LLM-Zugriff läuft über einen einzigen
OpenAI-kompatiblen Client, sodass der Provider ohne Code-Änderung austauschbar ist.

```ini
# ---- LLM (Default: GitHub Models — kostenlos, OpenAI-kompatibel, nutzt einen GitHub-PAT) ----
LLM_BASE_URL=https://models.github.ai/inference   # OpenAI-kompatibler Endpunkt
LLM_API_KEY=ghp_xxx                               # GitHub-PAT mit "models"-Berechtigung
LLM_CHAT_MODEL=openai/gpt-4o
LLM_VISION_MODEL=openai/gpt-4o                     # für die optionale Bildanalyse
# Wechsel zu OpenAI: LLM_BASE_URL=https://api.openai.com/v1, LLM_API_KEY=sk-...,
#   LLM_CHAT_MODEL=gpt-4o-mini

# ---- Datenbank ----
POSTGRES_USER=investa
POSTGRES_PASSWORD=change-me
POSTGRES_DB=offers
DATABASE_URL=postgresql+psycopg://investa:change-me@postgres:5432/offers

# ---- Externe Daten ----
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
OVERPASS_BASE_URL=https://overpass-api.de/api/interpreter
NOMINATIM_USER_AGENT=investa-offer-intel/0.1 (contact@example.com)

# ---- Scoring-Gewichte (auch via scoring.yaml überschreibbar) ----
SCORE_WEIGHT_LOCATION=0.30
SCORE_WEIGHT_PRICE=0.30
SCORE_WEIGHT_CONDITION=0.15
SCORE_WEIGHT_SIZE_USAGE=0.15
SCORE_WEIGHT_COMPLETENESS=0.10
```

> **Warum GitHub Models:** Es ist der legitime, kostenlose, rate-limitierte Weg, Top-Modelle (inkl.
> GPT-4o Vision) mit dem GitHub-Account über eine OpenAI-kompatible API zu nutzen. Das
> Copilot-Abonnement selbst ist nur für die In-Editor-Nutzung lizenziert, nicht als App-Backend — wir
> hängen zur Laufzeit also nicht davon ab.

### `docker-compose.yml`-Services
- `postgres` (mit `pg_trgm`; PostGIS-Image falls Geo-Distanz in SQL) + Named Volume → **Persistenz**.
- `backend` (FastAPI/uvicorn) — hängt von `postgres` ab, Healthcheck auf `/api/health`.
- `frontend` (Vite-Build via nginx) — proxyt `/api` zum Backend.
- Alles via `docker compose up` → **lokal lauffähig**, ein einzelner Befehl.

---

## 9. Bewusste Vereinfachungen

| Vereinfachung | Begründung |
|---------------|------------|
| Pipeline = FastAPI-Async-Background-Task (kein Celery/Redis) | Weniger bewegliche Teile für einen Prototyp; Status ist persistiert, die UX also identisch. Queue ist ein Drop-in-Upgrade. |
| Mietspiegel aus einer **mitgelieferten Seed-CSV** | Es existiert keine freie, umfassende Mietspiegel-API; ein kuratierter Datensatz je Region liefert realistische Benchmarks ohne Scraping. Quelle klar ausgewiesen. |
| Öffentliches Nominatim/Overpass (rate-limitiert) | Kostenlos & ohne Key; ausreichend für Prototyp-Volumina. Self-Hosting ist der Produktionspfad. |
| Antwort wird entworfen, nicht versendet | Versand ist in diesem Prototyp bewusst out of scope. |
| Demografie auf Gemeinde-Granularität | Wikidata-Abdeckung ist auf dieser Ebene verlässlich; feinere Daten erfordern bezahlte Quellen. |

---

## 10. Risiken & Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|--------|---------------|
| LLM-Halluzination bei fehlenden Feldern | Striktes JSON-Schema, `null` für Unbekanntes, Confidence-Feld, niedrige Temperatur |
| GitHub-Models-Rate-Limits | LLM- + Anreicherungs-Ergebnisse cachen; kleines Modell für Extraktion, Retries mit Backoff |
| Gescannte/verstümmelte PDFs | OCR-Fallback; niedrige Parse-Konfidenz im UI sichtbar machen |
| Geocoding-Treffer bei vagen Adressen | LLM-„Lage“-Inferenz + strukturierte Nominatim-Abfrage; `needs_review` markieren |
| Inkonsistente Dedup-Schwellen | Konfigurierbare Schwellen + `needs_review`-Band + gespeicherte Match-Evidenz |
