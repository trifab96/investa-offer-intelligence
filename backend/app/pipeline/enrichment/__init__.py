"""External data enrichment (4.4b — mandatory).

Each source is keyless/free where possible and every response is cached in the
DB with ``source`` + ``fetched_at`` (traceability + rate-limit friendliness).
"""
