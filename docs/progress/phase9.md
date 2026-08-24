# Phase 9 progress record

Phase 9 converts the browser-only prototype into a Windows-first installed endpoint platform.

Completed:

- removed all runtime demo-account creation and preset credentials;
- added concurrency-safe first-owner setup and a first-run React screen;
- added sensor registry/receipt tables and migration, including removal of the two historical
  deterministic demo accounts;
- added token-authenticated, fail-closed, deduplicated sensor ingestion;
- added a standard-library Windows sensor for supported event logs, suspicious process patterns,
  new high-risk listeners, and heartbeat/capability reporting;
- added the **This device** dashboard view and online/offline polling;
- added loopback-only desktop Compose, per-user install/start/stop scripts, and a PyInstaller bundle
  builder;
- added backend, frontend, sensor, migration, and installer validation.

The sensor does not install privileged persistence and never performs automatic remediation.
Broader protected-log access and public release publication remain separate explicit decisions.
