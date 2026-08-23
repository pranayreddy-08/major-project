# Dataset catalogue and governance

Last reviewed: 2026-08-23. The machine-readable identifiers and local paths are maintained in
`data/dataset-registry.json`. External datasets must be downloaded into the ignored
`data/external/` directory and must never be committed to this repository.

## Candidate public research datasets

### UNSW-NB15

- **Dataset ID:** `unsw-nb15-original`
- **Authoritative source:** [UNSW Research dataset page](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- **Version identity:** original UNSW-NB15 release; record the source-file name and download date in
  an experiment manifest because the publisher does not assign a semantic version.
- **Content/features:** approximately 100 GB of captured traffic, with PCAP, Bro, Argus, CSV, and
  report files. The published feature set contains 49 features and labels for nine attack families.
- **Licence/access:** free in perpetuity for academic research with required citations. Commercial
  use requires agreement from the authors.
- **Limitations:** traffic comes from a controlled cyber-range and combines generated normal and
  attack behavior. It is not representative of every modern organization, and its class balance,
  feature extraction, and lab topology can create shortcuts that do not transfer to production.

### CIC-IDS2017

- **Dataset ID:** `cic-ids2017`
- **Authoritative source:** [Canadian Institute for Cybersecurity dataset page](https://www.unb.ca/cic/datasets/ids-2017.html)
- **Version identity:** CIC-IDS2017, captured from 3-7 July 2017.
- **Content/features:** five days of PCAP and labeled flow CSV data, with more than 80
  CICFlowMeter-derived features. Scenarios include brute force, DoS/DDoS, Heartbleed, web attacks,
  infiltration, botnet activity, and benign traffic.
- **Licence/access:** publicly available for researchers; use requires citation of the dataset's
  associated paper as specified by the publisher.
- **Limitations:** this is a short controlled testbed capture. Attack families are associated with
  particular days and time windows, so random row splitting can leak scenario/time information and
  overstate generalization. Software, traffic patterns, and attacks also reflect 2017 conditions.

### CSE-CIC-IDS2018

- **Dataset ID:** `cse-cic-ids2018`
- **Authoritative source:** [CSE-CIC-IDS2018 dataset page](https://www.unb.ca/cic/datasets/ids-2018.html)
- **Version identity:** CSE-CIC-IDS2018 on AWS; record the downloaded object paths and date.
- **Content/features:** per-day PCAP and Windows/Linux logs plus more than 80 CICFlowMeter-V3
  features. The testbed models 420 machines, 30 servers, and seven attack scenarios.
- **Licence/access:** redistribution, republication, and mirroring are permitted when use includes
  the required dataset citation and a link to the publisher's AWS page.
- **Limitations:** the download is large, scenarios are profile-generated in a lab, and per-day
  organization can introduce temporal shortcuts. Feature-extractor versions and source object paths
  must be recorded to reproduce a result.

## Project-owned synthetic dataset

`synthetic-events-v1` is the default development and demonstration dataset. It is generated with a
fixed seed and uses only RFC 5737 documentation networks (`192.0.2.0/24` and
`198.51.100.0/24`), fabricated users, and fabricated hosts. It intentionally represents a small,
simple mix of benign connections, authentication failures, and port scans; it must not be used to
claim model effectiveness.

The adjacent manifest records its generator, seed, row count, schema version, and SHA-256 checksum.
Any change to generation logic or schema requires a new dataset ID and a new preprocessing config;
never silently replace an existing version.

`phase7-acceptance-events-v1` is a separate three-record raw JSON fixture that exercises field
aliases, ISO/naive/epoch-millisecond timestamps, normalization, correlation, explanation, and graph
construction. It uses only fabricated identities and RFC 5737 addresses. Its input checksum and
acceptance result are recorded in `docs/acceptance/phase7-synthetic-v1.json`; changing the records
requires a new fixture ID and acceptance record.

## Experiment recording policy

Every experiment must record:

- dataset ID, original filenames/object paths, source URL, download date, licence, and checksum;
- event-schema and preprocessing-config versions;
- chronological train/validation/test boundaries and row counts;
- selected features, label mapping, missing-value policy, and duplicate count;
- model parameters, metrics, and observed limitations.

Training transformations are fitted on the training partition only. Validation may be used for
tuning; the test partition is reserved for one final evaluation and must never guide feature,
parameter, threshold, or model selection.
