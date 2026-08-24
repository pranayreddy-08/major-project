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
9. **Threat scenarios** provides seven safe presentation cases covering credential abuse, malware,
   reconnaissance, lateral movement, exfiltration, suspicious administration, and normal activity.
10. **Feedback** records a human verdict and bounded comment.
11. **Audit log** is available to administrators.

## Present the threat scenarios

Open **Intelligence > Threat scenarios** and select **Run scenario**. Each case passes a synthetic,
clearly labelled event chain through the same Detection, Correlation, Risk, Explainability, and
Response agents used by normal analysis. The result panel compares the expected and actual class,
shows confidence and risk, identifies the graph and response outputs, and explains the evidence.

The scenarios cover all three detector outcomes:

| Scenario | Expected class | Why |
| --- | --- | --- |
| Credential attack | Attack | Repeated authentication failures followed by a successful login |
| Malware execution | Attack | Encoded PowerShell and a suspicious child process |
| Network reconnaissance | Attack | One source probes many destination ports in a short interval |
| Lateral movement | Attack | Remote service access and execution across internal hosts |
| Data exfiltration | Attack | Sensitive-file access followed by an unusually large outbound transfer |
| Suspicious tool activity | Suspicious | A dual-use administration tool runs without a confirmed attack chain |
| Normal activity | Benign | Routine sign-in and application traffic without threat indicators |

Scenario events and alerts are not written to the operational database. The result remains in the
current browser session for presentation, while the audit log records that a simulation was run.
The benign case intentionally creates no incident, attack graph, or response recommendation; this
demonstrates that the platform does not force every input into a threat class.

The platform never executes remediation automatically. Treat every detection as decision support:
verify the evidence, consider false positives, and use established incident-response procedures.

Use `installer\windows\Stop-ECTI.ps1` to stop the sensor and local containers. Database records
remain in the Docker volume.
