# Mutual Fund FAQ — Financial Document Ingestion and Retrieval

[![Offline parsing and data-lineage checks](https://github.com/yuktha-code/mutual_fund_FAQ/actions/workflows/offline-quality.yml/badge.svg)](https://github.com/yuktha-code/mutual_fund_FAQ/actions/workflows/offline-quality.yml)

A learning project for collecting official public mutual-fund documents, normalizing HTML/PDF content, preserving source metadata, generating search chunks and exploring source-backed factual question answering.

## Data sources and provenance

The source registry is in `data/sources.json`. It names public **AMFI**, **SEBI** and **asset-management company** webpages and scheme documents; each record includes a URL, source type, description, optional scheme association, fact types, fetch timestamp and content hash. These sources are public reference documents—not proprietary brokerage/customer data. The registry contains snapshots and references that may be outdated; **never treat an archived scheme value as a current investment disclosure** without checking the current issuer or regulator document.

## How the code is organized

1. **Source registration and fetch:** `scripts/phase1/fetch_corpus.py` reads the source registry, checks robots.txt, uses `requests` to retrieve material and records timestamps/hashes.
2. **Format parsing:** `scripts/phase1/parse_html.py` uses BeautifulSoup; `parse_pdf.py` uses pdfplumber. Navigation noise is removed, tables are serialized and image-only PDF pages are flagged rather than made up.
3. **Segmentation:** `scripts/phase2/chunk_corpus.py` creates token-bounded segments with overlaps and source metadata. `data/chunks.json` is an archived derived artifact; the original fetched-page corpus is not committed.
4. **Embedding/index design:** `scripts/phase2/embed_corpus.py` defines an OpenAI embedding workflow and Supabase indexing interface. `scripts/schema.sql` contains the PostgreSQL/pgvector table, cosine index and retrieval function. These are code/design assets, **not proof of a live database deployment today**.
5. **Query processing:** `scripts/phase3/` handles sanitizer, intent classification, query rewriting, retrieval and context assembly. `scripts/phase4/` and `app/` contain generated-answer and Next.js interface code.

## Testing and important limitations

- **Offline regression tests:** `python -m unittest discover -s tests -v`, run automatically in [GitHub Actions](https://github.com/yuktha-code/mutual_fund_FAQ/actions/workflows/offline-quality.yml).
- **Saved-report audit:** `python scripts/audit_saved_results.py` reports historical evaluation limitations; `--strict` returns an error code when archived issues exist.
- **Historic vector-index results:** `data/validation_results.json` reports **7 passed, 3 failed**. One other entry counted as a pass despite a missing expected fact type, because the earlier validator omitted the fact-type check. That pass criterion is now corrected for future runs.
- **Historic pipeline results:** `data/phase3_test_results.json` reported **10/10 passing return-type/guardrail checks**, but a Large Cap query was assigned an **ELSS** source. The revised tests also validate the expected scheme.
- **Historic generated-answer results:** `data/phase4_test_results.json` reported **8/8** on answer presence/refusal conditions, but that number does **not** mean 8/8 factually accurate answers. The Large Cap case includes an ELSS source URL. Future tests include scheme checks. Existing saved reports are archival and have not been silently altered.
- **Open questions:** retrieval correctness, source currency, actual answer citation fidelity and live hosted-service operation require fresh end-to-end evaluation with authorized API credentials. Offline green CI does not establish any of these.

## Reproduce the offline check

```bash
python -m unittest discover -s tests -v
python scripts/audit_saved_results.py
```

For live document-fetching and model-assisted workflows, see `architecture.md`, `requirements.txt`, `scripts/`, `.env.example`, and `scripts/schema.sql`. These workflows use external dependencies and credentials that are **not included** in the repository.

## Engineering lessons

Schema/format normalization, stable source IDs, provenance, safe handling of sensitive queries and test design matter as much as an LLM-generated answer. A nonempty answer and a plausible URL are **not** sufficient correctness checks; the correct scheme, fact type and source must match the user's requested document.

This is a technical demonstration and is **not investment advice**.
