# Data

Only small, anonymized samples and metadata may be committed here. Raw uploads, organizational logs,
large datasets, and derived artifacts are ignored by Git.

## Layout

| Directory | Git policy | Purpose |
| --- | --- | --- |
| `samples/` | Tracked | Small deterministic demo data and its checksum manifest |
| `raw/` | Ignored | Unmodified uploaded source records |
| `external/` | Ignored | Downloaded public research datasets |
| `processed/` | Ignored | Normalized events and model-ready features |
| `generated/` | Ignored | Temporary generator and pipeline outputs |

`synthetic-events-v1.csv` contains no real people, hosts, or routable addresses. Recreate it with
the generator command in the project README and compare its SHA-256 value with the adjacent
manifest. Dataset provenance and usage restrictions are recorded in `docs/datasets.md` and the
machine-readable `dataset-registry.json`.

`phase7-acceptance-events-v1.json` is a three-record raw-alias attack chain used only by the
end-to-end acceptance runner. Its SHA-256 digest and observed result are stored in
`docs/acceptance/phase7-synthetic-v1.json`.
