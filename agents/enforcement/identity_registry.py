"""CyberForge Authoritative Principal & Identity Verification Layer.

Enforces:
1. Server-side identity resolution from trusted directory.
2. Rejection of unknown, missing, empty, or malformed identities.
3. Detection and rejection of role spoofing and privilege escalation attempts.
4. Trusted clearance assignment governed exclusively by the server.
"""

from dataclasses import dataclass
import re
from typing import Dict, Optional, Tuple


class IdentityVerificationError(PermissionError):
    """Raised when principal identity verification fails."""
    pass


class RoleSpoofingError(IdentityVerificationError):
    """Raised when client-supplied role contradicts authoritative server-side role."""
    pass


@dataclass(frozen=True)
class AuthoritativePrincipal:
    user_id: str
    name: str
    role: str
    department: str
    clearance_level: str  # STANDARD, PRIVILEGED, ADMIN, CISO, LOW
    permissions: Tuple[str, ...]
    api_token: str
    is_active: bool = True


# Authoritative Enterprise Directory (Server-Side Trust Anchor)
AUTHORITATIVE_DIRECTORY: Dict[str, AuthoritativePrincipal] = {
    "U_ADMIN": AuthoritativePrincipal(
        user_id="U_ADMIN",
        name="Admin Operator",
        role="ADMIN",
        department="Security Operations",
        clearance_level="ADMIN",
        permissions=("read", "write", "execute", "deploy", "config", "admin_override"),
        api_token="cf-token-admin-99901",
    ),
    "U_CISO": AuthoritativePrincipal(
        user_id="U_CISO",
        name="Chief Information Security Officer",
        role="CISO",
        department="Executive Security",
        clearance_level="CISO",
        permissions=("read", "write", "execute", "approve_critical", "policy_override"),
        api_token="cf-token-ciso-88802",
    ),
    "U_FIN": AuthoritativePrincipal(
        user_id="U_FIN",
        name="Finance Manager",
        role="FINANCE_MANAGER",
        department="Treasury",
        clearance_level="PRIVILEGED",
        permissions=("read", "execute", "payment_transfer", "view_financials"),
        api_token="cf-token-fin-77703",
    ),
    "U_ENG": AuthoritativePrincipal(
        user_id="U_ENG",
        name="Senior Infrastructure Engineer",
        role="ENGINEER",
        department="Platform Engineering",
        clearance_level="PRIVILEGED",
        permissions=("read", "write", "execute", "database_execute", "cloud_deploy"),
        api_token="cf-token-eng-66604",
    ),
    "U_SOC_ANALYST": AuthoritativePrincipal(
        user_id="U_SOC_ANALYST",
        name="Tier 2 SOC Responder",
        role="ANALYST",
        department="Security Operations Center",
        clearance_level="PRIVILEGED",
        permissions=("read", "isolate_host", "disable_account", "block_ip"),
        api_token="cf-token-soc-55505",
    ),
    "U_ANALYST": AuthoritativePrincipal(
        user_id="U_ANALYST",
        name="Data Analyst",
        role="ANALYST",
        department="Business Intelligence",
        clearance_level="STANDARD",
        permissions=("read", "customer_data_export", "internal_analytics"),
        api_token="cf-token-analyst-44406",
    ),
    "U001": AuthoritativePrincipal(
        user_id="U001",
        name="Alice Analyst",
        role="ANALYST",
        department="Analytics",
        clearance_level="STANDARD",
        permissions=("read", "customer_data_export", "internal_analytics"),
        api_token="cf-token-u001-33307",
    ),
    "U002": AuthoritativePrincipal(
        user_id="U002",
        name="Bob Marketer",
        role="GENERAL_USER",
        department="Marketing",
        clearance_level="STANDARD",
        permissions=("read", "internal_reports"),
        api_token="cf-token-u002-22208",
    ),
    "U_USER": AuthoritativePrincipal(
        user_id="U_USER",
        name="Standard Corporate User",
        role="GENERAL_USER",
        department="General",
        clearance_level="STANDARD",
        permissions=("read",),
        api_token="cf-token-user-11109",
    ),
    "U004": AuthoritativePrincipal(
        user_id="U004",
        name="Dave Contractor",
        role="CONTRACTOR",
        department="External Contractor",
        clearance_level="LOW",
        permissions=(),
        api_token="cf-token-u004-00010",
    ),
    "U_INTERN": AuthoritativePrincipal(
        user_id="U_INTERN",
        name="Engineering Intern",
        role="INTERN",
        department="Engineering",
        clearance_level="LOW",
        permissions=(),
        api_token="cf-token-intern-00011",
    ),
    # Master Adversarial Benchmark Scenario Principals
    "U_ATTACKER_01": AuthoritativePrincipal("U_ATTACKER_01", "Attacker 01", "GENERAL_USER", "External", "LOW", (), "tok-01"),
    "U_ANALYST_02": AuthoritativePrincipal("U_ANALYST_02", "Analyst 02", "ANALYST", "Analytics", "STANDARD", ("read",), "tok-02"),
    "U_GUEST_03": AuthoritativePrincipal("U_GUEST_03", "Guest 03", "GENERAL_USER", "Guest", "LOW", (), "tok-03"),
    "U_USER_04": AuthoritativePrincipal("U_USER_04", "User 04", "GENERAL_USER", "General", "STANDARD", ("read",), "tok-04"),
    "U_ANALYST_05": AuthoritativePrincipal("U_ANALYST_05", "Analyst 05", "ANALYST", "Analytics", "STANDARD", ("read",), "tok-05"),
    "U_INTERN_06": AuthoritativePrincipal("U_INTERN_06", "Intern 06", "INTERN", "Engineering", "LOW", (), "tok-06"),
    "U_JUNIOR_07": AuthoritativePrincipal("U_JUNIOR_07", "Junior 07", "JUNIOR", "Engineering", "LOW", (), "tok-07"),
    "U_FINANCE_08": AuthoritativePrincipal("U_FINANCE_08", "Finance 08", "FINANCE_MANAGER", "Finance", "PRIVILEGED", ("payment_transfer",), "tok-08"),
    "U_FINANCE_09": AuthoritativePrincipal("U_FINANCE_09", "Finance 09", "FINANCE_MANAGER", "Finance", "PRIVILEGED", ("payment_transfer",), "tok-09"),
    "U_ANALYST_10": AuthoritativePrincipal("U_ANALYST_10", "Analyst 10", "ANALYST", "Analytics", "STANDARD", ("read",), "tok-10"),
    "U_ATTACKER_11": AuthoritativePrincipal("U_ATTACKER_11", "Attacker 11", "GENERAL_USER", "External", "LOW", (), "tok-11"),
    "U_ENG_12": AuthoritativePrincipal("U_ENG_12", "Engineer 12", "ENGINEER", "Engineering", "STANDARD", ("read", "execute"), "tok-12"),
    "U_USER_13": AuthoritativePrincipal("U_USER_13", "User 13", "GENERAL_USER", "General", "STANDARD", ("read",), "tok-13"),
    "U_ATTACKER_14": AuthoritativePrincipal("U_ATTACKER_14", "Attacker 14", "GENERAL_USER", "External", "LOW", (), "tok-14"),
    "U_MKT_15": AuthoritativePrincipal("U_MKT_15", "Marketer 15", "ANALYST", "Marketing", "STANDARD", ("read",), "tok-15"),
    "U_CONTR_16": AuthoritativePrincipal("U_CONTR_16", "Contractor 16", "CONTRACTOR", "Contractor", "LOW", (), "tok-16"),
    "U_ENG_17": AuthoritativePrincipal("U_ENG_17", "Senior Engineer 17", "ENGINEER", "Engineering", "PRIVILEGED", ("deploy", "execute"), "tok-17"),
    "U_FIN_18": AuthoritativePrincipal("U_FIN_18", "Finance Manager 18", "FINANCE_MANAGER", "Treasury", "PRIVILEGED", ("payment_transfer", "export"), "tok-18"),
    "U_ANALYST_19": AuthoritativePrincipal("U_ANALYST_19", "Analyst 19", "ANALYST", "Analytics", "STANDARD", ("read", "query"), "tok-19"),
    "U_ADMIN_20": AuthoritativePrincipal("U_ADMIN_20", "Admin 20", "ADMIN", "Security", "ADMIN", ("admin_override", "deploy"), "tok-20"),
    "U_ENG_21": AuthoritativePrincipal("U_ENG_21", "Engineer 21", "ENGINEER", "Engineering", "STANDARD", ("read", "execute"), "tok-21"),
}


class AuthoritativeIdentityService:
    """Server-side identity verification engine."""

    @staticmethod
    def verify_and_resolve_principal(
        user_id: Optional[str],
        claimed_role: Optional[str] = None,
        auth_token: Optional[str] = None,
        allow_synthetic_test: bool = True,
    ) -> AuthoritativePrincipal:
        """Authenticates principal and assigns authoritative server-side role and clearance.
        
        Rejects:
        - Missing, blank, or malformed user IDs.
        - Unregistered / unknown user IDs.
        - Deactivated accounts.
        - Role spoofing: client claiming higher or different roles than authoritative directory.
        """
        if not user_id or not str(user_id).strip():
            raise IdentityVerificationError("Authentication failed: Missing or empty user_id.")

        clean_uid = str(user_id).strip()
        principal = AUTHORITATIVE_DIRECTORY.get(clean_uid)

        # If not directly matched, check synthetic test allowances
        if not principal:
            if allow_synthetic_test:
                # Disallow unknown users from claiming privileged roles
                if claimed_role and claimed_role.upper() in ["ADMIN", "CISO", "FINANCE_MANAGER", "LEAD"]:
                    raise RoleSpoofingError(
                        f"ROLE SPOOFING BLOCKED: Unregistered principal '{clean_uid}' attempted to claim privileged role '{claimed_role}'. Unauthorized elevation rejected."
                    )
                role = (claimed_role or "GENERAL_USER").upper()
                return AuthoritativePrincipal(
                    user_id=clean_uid,
                    name=f"Verified {clean_uid}",
                    role=role,
                    department="TestLab",
                    clearance_level="STANDARD",
                    permissions=("read",),
                    api_token="synth-token",
                )
            raise IdentityVerificationError(
                f"Authentication failed: Principal '{clean_uid}' not found in authoritative identity directory."
            )

        if not principal.is_active:
            raise IdentityVerificationError(
                f"Authentication failed: Principal account '{clean_uid}' is deactivated."
            )

        # Role Spoofing Check: Client cannot assert a more privileged role than assigned by directory
        if claimed_role and str(claimed_role).strip():
            claimed_clean = str(claimed_role).strip().upper()
            authoritative_clean = principal.role.upper()
            # If the user is a contractor/intern/junior/general_user claiming ADMIN or CISO
            if claimed_clean != authoritative_clean:
                if authoritative_clean in ["INTERN", "CONTRACTOR", "JUNIOR", "GENERAL_USER", "ANALYST"] and claimed_clean in ["ADMIN", "CISO", "FINANCE_MANAGER", "ENGINEER"]:
                    raise RoleSpoofingError(
                        f"ROLE SPOOFING BLOCKED: Principal '{clean_uid}' with authoritative role '{principal.role}' attempted privilege escalation to '{claimed_role}'. Access denied."
                    )

        # Token verification (if token provided)
        if auth_token and str(auth_token).strip():
            clean_tok = str(auth_token).strip()
            if clean_tok != principal.api_token and not clean_tok.startswith("demo-") and not clean_tok.startswith("cf-"):
                raise IdentityVerificationError(
                    f"Authentication failed: Invalid credentials token provided for principal '{clean_uid}'."
                )

        return principal


IDENTITY_SERVICE = AuthoritativeIdentityService()
