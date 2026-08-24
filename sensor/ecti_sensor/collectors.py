import base64
import hashlib
import ipaddress
import json
import platform
import re
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ecti_sensor.state import SensorState

WINDOWS_EVENT_IDS = {
    1116: ("malware_detected", "critical", "detected", 1.0),
    1117: ("malware_remediation", "high", "blocked", 0.9),
    1121: ("attack_surface_reduction_blocked", "high", "blocked", 0.9),
    4625: ("authentication_failure", "medium", "failed", 0.72),
    5157: ("network_connection_blocked", "medium", "blocked", 0.62),
    7045: ("suspicious_service_installation", "high", "observed", 0.85),
}
SUSPICIOUS_COMMAND_PATTERNS = (
    (re.compile(r"(?i)(?:-|/)(?:enc|encodedcommand)\b"), "encoded PowerShell command"),
    (re.compile(r"(?i)frombase64string|downloadstring|invoke-expression"), "in-memory script"),
    (re.compile(r"(?i)\bmshta(?:\.exe)?\b.*https?://"), "remote HTA execution"),
    (re.compile(r"(?i)\bregsvr32(?:\.exe)?\b.*https?://"), "remote scriptlet execution"),
    (re.compile(r"(?i)\brundll32(?:\.exe)?\b.*(?:javascript:|https?://)"), "remote DLL execution"),
)
HIGH_RISK_LISTENER_PORTS = {1337, 4444, 5555, 6666, 31337}


@dataclass
class CollectionResult:
    events: list[dict[str, Any]]
    capabilities: dict[str, Any]
    next_state: SensorState


def _powershell_json(script: str, timeout: int = 30) -> list[dict[str, Any]]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = completed.stdout.strip()
    if not output:
        return []
    parsed = json.loads(output)
    return parsed if isinstance(parsed, list) else [parsed]


def _event_key(prefix: str, *parts: object) -> str:
    canonical = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _valid_ip(value: object) -> str | None:
    candidate = str(value or "").strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _event(
    key: str,
    timestamp: str,
    event_type: str,
    severity: str,
    action: str,
    log_source: str,
    hostname: str,
    anomaly_score: float,
    *,
    source_ip: str | None = None,
    user: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_key": key,
        "event": {
            "timestamp": timestamp,
            "source_ip": source_ip,
            "destination_ip": None,
            "user": user,
            "host": hostname,
            "protocol": None,
            "action": action,
            "severity": severity,
            "log_source": log_source,
            "event_type": event_type,
            "attributes": {"anomaly_score": anomaly_score, **(attributes or {})},
        },
    }


def suspicious_process_reason(name: str, path: str, command_line: str) -> str | None:
    combined = f"{name} {path} {command_line}"
    for pattern, reason in SUSPICIOUS_COMMAND_PATTERNS:
        if pattern.search(combined):
            return reason
    lowered = path.lower()
    temporary = "\\temp\\" in lowered or "\\appdata\\local\\temp\\" in lowered
    if temporary and lowered.endswith((".exe", ".dll", ".ps1", ".vbs", ".js")):
        return "executable launched from a temporary directory"
    return None


def map_windows_event(record: dict[str, Any], hostname: str) -> dict[str, Any] | None:
    event_id = int(record.get("Id", 0))
    mapping = WINDOWS_EVENT_IDS.get(event_id)
    if mapping is None:
        return None
    event_type, severity, action, anomaly_score = mapping
    data = record.get("Data") if isinstance(record.get("Data"), dict) else {}
    timestamp = str(record.get("TimeCreated") or datetime.now(timezone.utc).isoformat())
    provider = str(record.get("ProviderName") or "Windows")
    attributes: dict[str, Any] = {
        "windows_event_id": event_id,
        "provider": provider[:255],
        "record_id": record.get("RecordId"),
    }
    if event_id in {1116, 1117}:
        threat_name = str(data.get("Threat Name") or data.get("ThreatName") or "").strip()
        if threat_name:
            attributes["threat_name"] = threat_name[:255]
    if event_id == 7045:
        service_name = str(data.get("ServiceName") or "").strip()
        image_path = str(data.get("ImagePath") or "").strip()
        attributes["service_name"] = service_name[:255]
        if image_path:
            attributes["image_path_sha256"] = hashlib.sha256(image_path.encode()).hexdigest()
    return _event(
        f"winevent:{provider}:{record.get('RecordId', event_id)}",
        timestamp,
        event_type,
        severity,
        action,
        "windows-event-log",
        hostname,
        anomaly_score,
        source_ip=_valid_ip(data.get("IpAddress")),
        user=str(data.get("TargetUserName") or "").strip() or None,
        attributes=attributes,
    )


def _windows_events(since: str, hostname: str) -> tuple[list[dict[str, Any]], bool]:
    script = f"""
$start=[DateTime]::Parse('{since}').ToUniversalTime()
$queries=@(
 @{{LogName='Microsoft-Windows-Windows Defender/Operational'
    Id=@(1116,1117,1121);StartTime=$start}},
 @{{LogName='Security';Id=@(4625,5157);StartTime=$start}},
 @{{LogName='System';Id=@(7045);StartTime=$start}}
)
$results=@()
foreach($query in $queries){{
 try{{
  Get-WinEvent -FilterHashtable $query -ErrorAction Stop|ForEach-Object{{
   $data=@{{}};[xml]$xml=$_.ToXml()
   foreach($node in $xml.Event.EventData.Data){{
    if($node.Name){{$data[$node.Name]=[string]$node.'#text'}}
   }}
   $results += [pscustomobject]@{{
    RecordId=$_.RecordId;TimeCreated=$_.TimeCreated.ToUniversalTime().ToString('o')
    Id=$_.Id;ProviderName=$_.ProviderName;Data=$data
   }}
  }}
 }}catch{{}}
}}
$results|ConvertTo-Json -Depth 6 -Compress
"""
    try:
        records = _powershell_json(script)
        events = [mapped for record in records if (mapped := map_windows_event(record, hostname))]
        return events, True
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return [], False


def _suspicious_processes(
    hostname: str, observed_at: str, previous: set[str]
) -> tuple[list[dict[str, Any]], set[str], bool]:
    script = """
Get-CimInstance Win32_Process|
 Select-Object ProcessId,Name,ExecutablePath,CommandLine|
 ConvertTo-Json -Depth 3 -Compress
"""
    try:
        processes = _powershell_json(script)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return [], previous, False
    active: set[str] = set()
    events: list[dict[str, Any]] = []
    for process in processes:
        name = str(process.get("Name") or "")
        path = str(process.get("ExecutablePath") or "")
        command = str(process.get("CommandLine") or "")
        reason = suspicious_process_reason(name, path, command)
        if reason is None:
            continue
        fingerprint = hashlib.sha256(f"{path}|{command}".encode()).hexdigest()
        active.add(fingerprint)
        if fingerprint in previous:
            continue
        events.append(
            _event(
                _event_key("process", fingerprint, observed_at),
                observed_at,
                "suspicious_process_execution",
                "high",
                "observed",
                "windows-process-sensor",
                hostname,
                0.9,
                attributes={
                    "process_name": name[:255],
                    "executable_path": path[:500],
                    "command_line_sha256": hashlib.sha256(command.encode()).hexdigest(),
                    "reason": reason,
                    "process_id": process.get("ProcessId"),
                },
            )
        )
    return events, active, True


def _new_high_risk_listeners(
    hostname: str, observed_at: str, previous: set[str], initialized: bool
) -> tuple[list[dict[str, Any]], set[str], bool]:
    script = """
Get-NetTCPConnection -State Listen|
 Select-Object LocalAddress,LocalPort,OwningProcess|
 ConvertTo-Json -Depth 3 -Compress
"""
    try:
        listeners = _powershell_json(script)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return [], previous, initialized
    active = {
        f"{item.get('LocalAddress')}:{item.get('LocalPort')}:{item.get('OwningProcess')}"
        for item in listeners
    }
    events: list[dict[str, Any]] = []
    if initialized:
        for item in listeners:
            port = int(item.get("LocalPort") or 0)
            fingerprint = f"{item.get('LocalAddress')}:{port}:{item.get('OwningProcess')}"
            if fingerprint in previous or port not in HIGH_RISK_LISTENER_PORTS:
                continue
            events.append(
                _event(
                    _event_key("listener", fingerprint, observed_at),
                    observed_at,
                    "suspicious_network_listener",
                    "medium",
                    "observed",
                    "windows-network-sensor",
                    hostname,
                    0.7,
                    attributes={
                        "local_address": str(item.get("LocalAddress") or "")[:45],
                        "local_port": port,
                        "process_id": item.get("OwningProcess"),
                        "reason": "new listener on a commonly abused high-risk port",
                    },
                )
            )
    return events, active, True


def local_ip_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None):
            candidate = _valid_ip(item[4][0])
            if candidate and not ipaddress.ip_address(candidate).is_loopback:
                addresses.add(candidate)
    except OSError:
        pass
    return sorted(addresses)


def collect(state: SensorState, observed_at: datetime | None = None) -> CollectionResult:
    now = observed_at or datetime.now(timezone.utc)
    now_text = now.isoformat()
    next_state = SensorState(
        last_successful_observation=now_text,
        active_suspicious_processes=list(state.active_suspicious_processes),
        active_listeners=list(state.active_listeners),
        listeners_initialized=state.listeners_initialized,
    )
    if platform.system() != "Windows":
        return CollectionResult(
            events=[],
            capabilities={
                "windows_event_log": False,
                "process_monitor": False,
                "network_monitor": False,
            },
            next_state=next_state,
        )
    hostname = socket.gethostname()
    event_events, event_ok = _windows_events(state.last_successful_observation, hostname)
    process_events, processes, process_ok = _suspicious_processes(
        hostname, now_text, set(state.active_suspicious_processes)
    )
    listener_events, listeners, listener_ok = _new_high_risk_listeners(
        hostname, now_text, set(state.active_listeners), state.listeners_initialized
    )
    next_state.active_suspicious_processes = sorted(processes)
    next_state.active_listeners = sorted(listeners)
    next_state.listeners_initialized = listener_ok
    return CollectionResult(
        events=event_events + process_events + listener_events,
        capabilities={
            "windows_event_log": event_ok,
            "process_monitor": process_ok,
            "network_monitor": listener_ok,
            "privacy_mode": "command-lines-hashed",
        },
        next_state=next_state,
    )
