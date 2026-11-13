# Architecture

The diagram and component descriptions are completed as each phase lands.

```mermaid
flowchart LR
    raw[Raw IBGE files<br/>fixed-width + SAS input + dictionary] --> ingest[ingest]
    raw --> metadata[metadata]
    ingest --> interim[(Interim Parquet)]
    metadata --> catalog[(Variable catalog)]
    schema[harmonized_schema.yaml] --> mapping
    catalog --> mapping[mapping<br/>retrieval + LLM]
    mapping --> proposed[mappings/proposed]
    proposed --> review{{Human review}}
    review --> approved[mappings/approved]
    interim --> transform[transform]
    approved --> transform
    transform --> harmonized[(Harmonized Parquet)]
    harmonized --> quality[quality]
    harmonized --> indicators[indicators]
    quality --> qc[QC report]
    indicators --> pov[Poverty and inequality report]
```

Design principle: everything survey-specific lives in `config/surveys/*.yaml`
and `mappings/`; the code under `src/lacharm/` is survey-agnostic.
