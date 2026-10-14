"""CyberForge Deterministic Simulated Infrastructure & Protected Resource Store.

Manages the 5 core enterprise simulation entities:
1. Normal Workstation (workstation-alice-01)
2. Compromised Workstation (host-workstation-42)
3. Critical Server (srv-domain-controller-01)
4. Simulated User Account (john_doe)
5. Network Access Control State (perimeter_firewall blocked IPs)

Captures full state before, state after, and delta to prove empirically
that blocked actions produce zero side effects on target resources.
"""

from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class NormalWorkstationState:
    id: str = "workstation-alice-01"
    hostname: str = "workstation-alice-01"
    owner: str = "Alice Analyst"
    status: str = "ONLINE"
    isolated: bool = False
    compromised: bool = False
    isolation_mode: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CompromisedWorkstationState:
    id: str = "host-workstation-42"
    hostname: str = "host-workstation-42"
    owner: str = "Bob Marketer"
    status: str = "ONLINE"
    isolated: bool = False
    compromised: bool = True
    threat_indicator: str = "CobaltStrike Beacon / Emotet Payload"
    isolation_mode: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CriticalServerState:
    id: str = "srv-domain-controller-01"
    hostname: str = "srv-domain-controller-01"
    role: str = "Active Directory & Core Kerberos Authentication"
    tier: str = "TIER_0_CRITICAL"
    status: str = "ONLINE"
    service_state: str = "RUNNING"
    maintenance_mode: bool = False
    reboot_pending: bool = False
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SimulatedUserAccountState:
    id: str = "user_john_doe"
    username: str = "john_doe"
    display_name: str = "John Doe"
    status: str = "ACTIVE"
    sessions_revoked: bool = False
    lockout_reason: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class NetworkAccessControlState:
    id: str = "perimeter_firewall"
    name: str = "Corporate Edge Firewall / WAF"
    default_policy: str = "ALLOW_ESTABLISHED"
    blocked_ips: List[str] = field(default_factory=list)
    blocked_destinations: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SimulatedInfrastructureStore:
    """Thread-safe deterministic enterprise infrastructure store."""

    def __init__(self):
        self._lock = threading.Lock()
        self.normal_workstation = NormalWorkstationState()
        self.compromised_workstation = CompromisedWorkstationState()
        self.critical_server = CriticalServerState()
        self.user_account = SimulatedUserAccountState()
        self.firewall = NetworkAccessControlState()

    def snapshot(self) -> Dict[str, Any]:
        """Returns deep-copied snapshot of all 5 infrastructure entities."""
        with self._lock:
            return {
                "workstation_normal": asdict(self.normal_workstation),
                "workstation_compromised": asdict(self.compromised_workstation),
                "server_critical": asdict(self.critical_server),
                "user_account": asdict(self.user_account),
                "network_access_control": asdict(self.firewall),
            }

    def reset(self):
        """Resets all simulation entities to canonical initial benchmark state."""
        with self._lock:
            self.normal_workstation = NormalWorkstationState()
            self.compromised_workstation = CompromisedWorkstationState()
            self.critical_server = CriticalServerState()
            self.user_account = SimulatedUserAccountState()
            self.firewall = NetworkAccessControlState()

    def isolate_host(self, hostname: str, isolation_mode: str = "FULL") -> Dict[str, Any]:
        """Executes host network isolation."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            if hostname in ["host-workstation-42", self.compromised_workstation.id]:
                self.compromised_workstation.isolated = True
                self.compromised_workstation.status = "ISOLATED"
                self.compromised_workstation.isolation_mode = isolation_mode
                self.compromised_workstation.last_updated = now
                return {"target": hostname, "isolated": True, "entity": asdict(self.compromised_workstation)}
            elif hostname in ["workstation-alice-01", self.normal_workstation.id]:
                self.normal_workstation.isolated = True
                self.normal_workstation.status = "ISOLATED"
                self.normal_workstation.isolation_mode = isolation_mode
                self.normal_workstation.last_updated = now
                return {"target": hostname, "isolated": True, "entity": asdict(self.normal_workstation)}
            elif hostname in ["srv-domain-controller-01", self.critical_server.id]:
                self.critical_server.status = "ISOLATED"
                self.critical_server.last_updated = now
                return {"target": hostname, "isolated": True, "entity": asdict(self.critical_server)}
            else:
                return {"target": hostname, "isolated": True, "note": f"Generic host '{hostname}' isolated."}

    def disable_user_account(self, username: str, reason: str = "") -> Dict[str, Any]:
        """Disables an enterprise account and revokes active tokens."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.user_account.status = "DISABLED"
            self.user_account.sessions_revoked = True
            self.user_account.lockout_reason = reason or "Security response action"
            self.user_account.last_updated = now
            return {"username": username, "status": "DISABLED", "entity": asdict(self.user_account)}

    def block_network_destination(self, destination: str, direction: str = "BOTH") -> Dict[str, Any]:
        """Adds IP or domain to perimeter firewall blocklist."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            if destination not in self.firewall.blocked_ips:
                self.firewall.blocked_ips.append(destination)
            self.firewall.last_updated = now
            return {
                "destination": destination,
                "blocked": True,
                "total_blocked": len(self.firewall.blocked_ips),
                "entity": asdict(self.firewall),
            }

    def restart_service(self, service_name: str, server_id: str) -> Dict[str, Any]:
        """Restarts a high-impact critical infrastructure service."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.critical_server.reboot_pending = False
            self.critical_server.service_state = "RESTARTED"
            self.critical_server.last_updated = now
            return {"service": service_name, "server": server_id, "status": "RESTARTED"}

    def disable_critical_server(self, server_id: str, reason: str = "") -> Dict[str, Any]:
        """DESTRUCTIVE: Attempts to decommission or disable a Tier-0 server."""
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.critical_server.status = "OFFLINE"
            self.critical_server.service_state = "TERMINATED"
            self.critical_server.last_updated = now
            return {"server_id": server_id, "status": "OFFLINE"}


# Global Deterministic Simulated Infrastructure Store
INFRASTRUCTURE_STORE = SimulatedInfrastructureStore()
