# Normalized event contract

Every ingestion adapter must preserve its source record in `raw_events` and produce this common
shape before detection or correlation. The Pydantic contract is
`backend/app/schemas/events.py::NormalizedEventCreate`.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `timestamp` | ISO 8601 datetime with timezone | Yes | When the source event occurred |
| `source_ip` | IPv4 or IPv6 address | No | Originating network address |
| `destination_ip` | IPv4 or IPv6 address | No | Target network address |
| `user` | String | No | Account associated with the event |
| `host` | String | No | Hostname or asset identifier |
| `protocol` | String | No | Network/application protocol |
| `action` | String | No | Source action such as allowed, denied, or login_failed |
| `severity` | Enum | Yes | `informational`, `low`, `medium`, `high`, or `critical` |
| `log_source` | String | Yes | Producing system, such as firewall or endpoint |
| `event_type` | String | Yes | Normalized event category |
| `raw_event_id` | UUID | No | Reference to the preserved source event |
| `attributes` | JSON object | No | Source-specific fields not in the common schema |

Example:

```json
{
  "timestamp": "2026-01-15T08:30:00Z",
  "source_ip": "192.0.2.10",
  "destination_ip": "198.51.100.7",
  "user": "analyst",
  "host": "workstation-01",
  "protocol": "TCP",
  "action": "allowed",
  "severity": "medium",
  "log_source": "firewall",
  "event_type": "network_connection",
  "attributes": {"destination_port": 443}
}
```

Adapters must convert timestamps to timezone-aware values, validate IP addresses, retain unknown
fields in `attributes`, and reject records that cannot satisfy the required fields.
