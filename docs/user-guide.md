# Phase 6 analyst dashboard guide

Start the stack with `docker compose up --build`, then open <http://localhost:5173>. Sign in with the
local analyst account shown on the login screen. The token is held only for the current page session;
refreshing or signing out requires a new login.

## Views

1. **Overview** shows open alerts, active incidents, critical signals, monitored-event count,
   severity distribution, recent activity, model version, and the human-approval guarantee.
2. **Alert queue** filters alerts by text and severity. Selecting a row opens its explanation.
3. **Incident** shows the correlated timeline, risk score, and safe recommended actions.
4. **Attack graph** renders incident entities and relationships with Cytoscape.js. Select a node to
   inspect its type/risk. Graph edges support investigation but do not prove causality.
5. **Explainability** shows confidence, analyst-readable reasoning, important evidence, limitations,
   and advisory recommendations.
6. **Feedback** lets an analyst confirm, dismiss, or flag an alert and add a bounded comment.
7. **Audit log** is visible only when signed in as the administrator account.

The workspace starts with deterministic synthetic data. No real organizational logs, credentials,
or indicators are included. All response cards explicitly state that approval is required and no
automatic execution is possible.
