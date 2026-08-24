# Local endpoint dashboard guide

Open <http://127.0.0.1:8080> for an installed bundle or <http://localhost:5173> during development.

## First launch

A new installation shows **Create platform owner**. Choose your own username, full name, and a
password of at least 12 characters. There are no demo credentials. This page disappears after the
first administrator is created; later sessions use the normal sign-in form. The bearer token remains
only in memory, so refreshing or signing out requires another login.

## Confirm local protection

Open **This device**. A healthy installation shows the Windows endpoint sensor as online, its last
heartbeat, operating system, agent version, local IP addresses, and enabled collection capabilities.
It can take about one collection interval (60 seconds by default) to appear.

If it is offline, run `installer\windows\Start-ECTI.ps1`, confirm Docker Desktop is running, then
inspect `%LOCALAPPDATA%\ECTI\data\sensor.log`. Some protected Windows event channels require
elevation; the standard installer intentionally runs without it.

## Investigation views

1. **Home** summarizes security state and guides a new user through Collect, Triage, Understand, and
   Decide actions.
2. **This device** reports whether real host telemetry is reaching the platform.
3. **Alert queue** filters detections and opens their explanations.
4. **Incident** correlates the timeline, risk score, and safe response recommendations.
5. **Attack graph** visualizes entities and relationships. Edges assist investigation but do not
   prove causality.
6. **Why this alert?** shows confidence, reasoning, evidence, limitations, and recommendations.
7. **Agent workflow** shows the latest Detection → Correlation → Risk → Explainability → Response
   run, including status, duration, handoff digests, and the mandatory human gate.
8. **Models & GNN** distinguishes the live deterministic detector from offline Logistic Regression
   and causal GraphSAGE evaluation, including architecture, metrics, dataset, and limitations.
9. **Feedback** records a human verdict and bounded comment.
10. **Audit log** is available to administrators.

The platform never executes remediation automatically. Treat every detection as decision support:
verify the evidence, consider false positives, and use established incident-response procedures.

Use `installer\windows\Stop-ECTI.ps1` to stop the sensor and local containers. Database records
remain in the Docker volume.
