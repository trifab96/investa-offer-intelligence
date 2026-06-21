# Fachliche Präsentation — Investa Offer Intelligence

> **KI Challenge — Forward Deployed Engineer (AI / GenAI)** · Bassem Trifa
> Publikum: **Christian Femerling (Geschäftsführer / CEO)**, Aleksandra Vojinovic
> Format: remote (MS Teams). **~30 Minuten gesamt** → ~18–20 Min Vortrag + ~10 Min Diskussion einplanen.
> Fokus (laut Einladung): Verständnis der Problemstellung · Lösung & Ergebnisse · KI/LLM im Kontext ·
> Einordnung der Ergebnisse & Abwägung von Alternativen.

---

## Haltung für dieses Publikum
- Das ist der **CEO**, nicht das IT-Panel. Über **geschäftlichen Wert, Entscheidungen, Risiko** reden —
  nicht über Code.
- Alles in **gesparte Zeit, nicht verpasste Deals, vermiedene Fehler** verankern.
- Das **funktionierende Produkt** zeigen und es sprechen lassen; Jargon weglassen („Dubletten-Prüfung“
  statt „Fuzzy Matching“; „Marktdaten“ statt „Overpass API“).
- Ehrlich zu Grenzen sein — ein CEO vertraut jemandem, der die Grenzen des eigenen Tools benennt.
- ~8 Folien, ~2 Min je, plus eine 4-Minuten-Live-Demo.

---

## FOLIE 1 — Das Problem, in Investas Worten (2 Min)

- Investa erhält einen **konstanten Strom an Maklerangeboten** per E-Mail + PDF. Ein realer
  Deal-Flow-Kanal — aber **verrauscht**:
  - viele sind **bereits bekannt** (und erneut angeboten, mit Provisionsstreit-Risiko),
  - viele sind **wirtschaftlich unattraktiv**,
  - viele sind **unvollständig oder schwer vergleichbar**.
- Heute liest eine Fachkraft jedes Angebot manuell. Das ist **langsam, teuer und inkonsistent** — und
  die guten Angebote können untergehen.

> Eröffnungssatz: *„Die Frage, die ich mir gestellt habe, war simpel: Von den Angeboten, die diese
> Woche im Posteingang landen, welche drei sind tatsächlich die Zeit eines Analysten wert? Heute heißt
> das herauszufinden: alle lesen. Meine Lösung beantwortet es in Sekunden.“*

---

## FOLIE 2 — Was ich gebaut habe (2 Min) — *ein Satz + das Dashboard*

> *„Ein Tool, das jedes eingehende Angebot liest, prüft ob wir es bereits kennen, mit Marktdaten
> anreichert und ihm einen 0–10-Attraktivitäts-Score mit klarer Empfehlung gibt — aus einem vollen
> Posteingang wird eine kurze, priorisierte Liste.“*

- Das **Dashboard** zeigen: Kennzahlen + Score-Verteilung + Top-Angebote.
- *„Statt 30 PDFs zu lesen, schauen Sie auf die 3 grünen.“*

---

## FOLIE 3 — Live-Demo (4 Min) — *das Herz des Vortrags*

**Ein Angebot** Ende zu Ende durchgehen, in geschäftlichen Begriffen erzählen:

1. **Hochladen** der Geesthacht-E-Mail (`.msg`) — *„eine echte Makler-E-Mail mit angehängtem PDF.“*
2. **Extrahierte Fakten** — *„es hat Typ, Lage, Größe, Preis, Zustand automatisch herausgezogen — und
   berichtet nur, was wirklich im Dokument steht, rät nie.“*
3. **Markt-Anreicherung + Karte** — *„es hat die Immobilie verortet und Bevölkerung, lokale
   Infrastruktur und eine Referenzmiete ergänzt — alles aus öffentlichen Daten.“*
4. **Der Score: 6.96 / „Einkommensobjekt“** — *„und entscheidend: es hat das als Einkommensobjekt
   bewertet — es hat auf Vermietungsstand und Mietsteigerungspotenzial geschaut, nicht auf dieselbe
   Checkliste wie für ein Baugrundstück.“*
5. **Top-Treiber + Risiken/Chancen** — *„hier ist, warum es so bewertet hat, in Klartext.“*
6. **Erneut hochladen** → *„bereits bekannt, keine Provision“-Antwort* — *„und es entwirft eine
   höfliche Antwort an den Makler. Ein direkter Zeitgewinn und es vermeidet Provisionsstreit.“*

---

## FOLIE 4 — Ergebnisse auf den echten Angeboten (2 Min)

| Angebot | Erkannt als | Score | Empfehlung |
|---------|-------------|-------|------------|
| Geesthacht — vermietete Wohnanlage | Einkommensobjekt | 6.96 | Prüfen |
| Bad Homburg — Büro | Gewerbeobjekt | 8.85 | Verfolgen |
| Raintal-Höfe — Bauland (München) | Entwicklungsgrundstück | 6.45 | Prüfen |
| Hamburg — Grundstück mit Bestand | Entwicklungsgrundstück | 4.70 | Prüfen |
| Bernau / Bürgerstraße (erneut) | **Bereits bekannt** | — | Auto-Antwort, keine Provision |

- Der Punkt sind nicht die exakten Zahlen — sondern dass **jedes als das verstanden wurde, was es
  ist**, und konsistent eingeordnet, in Sekunden, mit beigefügter Begründung.

---

## FOLIE 5 — Warum die Bewertung verlässlich ist (2 Min) — *die Domänenverständnis-Folie*

- Ein Immobilien-Profi bewertet ein **Baugrundstück** anders als ein **vermietetes MFH** oder ein
  **Büro**. Ein naives Tool, das alles gleich bewertet, wäre für Sie **sichtbar falsch**.
- Daher **erkennt das Tool zuerst den Objekttyp** und wendet dann die **richtigen Kriterien** an:
  - Bauland → wie viel bebaubar, Lage, Preis je künftiger Einheit
  - Einkommensobjekt → Rendite, **wie voll vermietet**, Mietsteigerungspotenzial
  - Gewerbe → Rendite, Vermietung, Lage
- Es **bestraft echte Risiken** (Altlast, Erbpacht, Leerstand) und **zeigt die Top-Faktoren** hinter
  jedem Score. Nichts ist eine Blackbox.

> Das ist der Satz, der beim CEO landet: *„Es denkt wie ein Analyst — es weiß, dass ‚ist es schon
> vermietet‘ beim MFH zählt, beim Grundstück aber irrelevant ist.“*

---

## FOLIE 6 — Wo KI eingesetzt wird (und wo nicht) (2 Min)

- **KI (das Sprachmodell) übernimmt das Urteil:** unsaubere E-Mails/PDFs lesen, Fakten ziehen,
  Lagebegehrtheit einschätzen, Risiken und Chancen benennen, die Bilder lesen, Antworten entwerfen.
- **Klassische Berechnung übernimmt die Zahlen:** Rendite, €/m², Distanzen. *„Bewusst lasse ich die KI
  nicht rechnen — darin ist sie nicht verlässlich. Die KI interpretiert; das System rechnet.“*
- **Warum das für Sie zählt:** jede Zahl ist **reproduzierbar und erklärbar**, und Sie sehen die
  exakte Begründung hinter jedem Ergebnis. KI dort, wo sie Mehrwert schafft, nicht um ihrer selbst willen.

---

## FOLIE 7 — Ehrliche Grenzen & Alternativen (2 Min) — *schafft Vertrauen*

- Es ist ein **Entscheidungs-Unterstützungs-Prototyp, kein Auto-Kauf** — ein Mensch entscheidet immer.
  Es **priorisiert**, ersetzt nicht das Urteil.
- Manche Daten sind **öffentlich und approximativ** (z. B. der Referenzmiet-Datensatz ist ein
  kuratiertes Sample); in Produktion wird das gegen einen lizenzierten Marktdaten-Feed getauscht.
- Es kann sich irren — deshalb **zeigt es seine Confidence**, **markiert Angebote mit dünner Datenlage**
  und **erklärt sich**, sodass ein Analyst es übersteuern kann.
- **Abgewogene Alternativen:** ein einfacher reiner Regelfilter (zu starr für unsaubere Angebote); eine
  reine LLM-Bewertung (nicht auditierbar, halluzinationsanfällig). Ich habe den **hybriden** Weg
  gewählt, gerade weil er klug *und* erklärbar ist.

---

## FOLIE 8 — Geschäftlicher Wert & nächste Schritte (2 Min)

- **Wert:** schnellere Triage, keine verpassten guten Angebote, weniger Provisionsstreit, konsistente
  und dokumentierte Entscheidungen — Fachkräfte investieren Zeit nur in die relevanten Angebote.
- **Passt zu Investa:** darauf gebaut, an Ihre bestehenden Daten (SAP, SharePoint) und einen echten
  Mietspiegel-Feed anzudocken — die Architektur ist bereit dafür.
- **Bei Weiterführung:** interne Daten integrieren, eine „needs review“-Queue für Grenzfälle ergänzen
  und aus den Annehmen/Ablehnen-Entscheidungen der Analysten lernen, um das Scoring über Zeit zu schärfen.

> Abschluss: *„In drei Tagen habe ich ein funktionierendes Tool gebaut, das Ihre eingehenden Angebote
> liest, den Unterschied zwischen einem Grundstück und einem vermieteten Gebäude kennt und Ihnen sagt,
> wo Sie zuerst hinschauen sollten — mit beigefügter Begründung. Das ist die Art praktischer,
> wirkungsvoller KI, die ich hier weiter bauen möchte.“*

---

## Q&A-Bank — fachlich

- *„Kann es sich irren?“* → Ja, und es ist darauf ausgelegt, ehrlich damit umzugehen: es zeigt
  Confidence, markiert Angebote mit dünner Datenlage und erklärt jeden Score, sodass ein Analyst
  übersteuern kann. Es priorisiert, es entscheidet nicht.
- *„Inwiefern besser als ein Analyst?“* → Es ist nicht klüger — es ist schneller und konsistent. Es
  macht den ersten Durchlauf in Sekunden, damit der Analyst seine Expertise nur auf die Shortlist legt.
- *„Was ist mit unseren eigenen Daten — kennen wir das Objekt schon?“* → Das ist ein Kern-Feature: es
  führt eine Registry bekannter Objekte und markiert Wiedereinreichungen automatisch. Mit
  angebundenen internen Systemen wird diese Registry weit reichhaltiger.
- *„Wie viel kostet der Betrieb?“* → Für den Prototyp nichts — es nutzt eine kostenlose KI-Stufe und
  freie öffentliche Daten. Im Maßstab sind die Hauptkosten die KI-Calls (Cents je Angebot) und ein
  lizenzierter Daten-Feed.
- *„Wie lange bis zur Produktionsreife?“* → Der Kern funktioniert heute; Produktion heißt interne
  Daten integrieren, härten und einen Review-Workflow — eine fokussierte nächste Phase, kein Neubau.
- *„Sind unsere Daten sicher / verlassen sie das Haus?“* → Angebote werden von einem LLM-Provider
  verarbeitet; das ist konfigurierbar und kann auf ein Enterprise-/Azure- oder privates Modell zeigen
  — eine Deployment-Entscheidung, der Code ändert sich nicht.
- *„Warum sollten wir dem Score vertrauen?“* → Weil er keine Blackbox ist: asset-typ-bewusst, jeder
  Faktor gezeigt, jeder KI-Prompt protokolliert. Sie können jede Zahl bis zur Quelle auditieren.

---

## Timing-Spickzettel (30 Min)
| Abschnitt | Min |
|-----------|-----|
| Problem (F1) | 2 |
| Was ich gebaut habe (F2) | 2 |
| **Live-Demo (F3)** | 4 |
| Ergebnisse (F4) | 2 |
| Verlässliches Scoring (F5) | 2 |
| KI-Einsatz (F6) | 2 |
| Grenzen & Alternativen (F7) | 2 |
| Wert & nächste Schritte (F8) | 2 |
| **Q&A** | ~10 |
