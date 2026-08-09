import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from dataclasses import dataclass

@dataclass
class AllowedAction:
    name: str
    description: str
    required_permissions: list[str]
    data_sensitivity: str  # low, medium, high, critical
    allowed_targets: list[str]

ACTION_REGISTRY = {
    'read_customer_summary': AllowedAction(
        name='read_customer_summary',
        description='Read aggregated customer analytics summary',
        required_permissions=['read_customer_summary'],
        data_sensitivity='low',
        allowed_targets=['internal-analytics', 'approved-internal-analytics']
    ),
    'export_anonymized_report': AllowedAction(
        name='export_anonymized_report',
        description='Export anonymized/aggregated analytics report',
        required_permissions=['export_anonymized_report'],
        data_sensitivity='medium',
        allowed_targets=['approved-internal-analytics', 'approved-analytics-service']
    ),
    'send_internal_report': AllowedAction(
        name='send_internal_report',
        description='Send report to internal stakeholders',
        required_permissions=['send_internal_report'],
        data_sensitivity='medium',
        allowed_targets=['internal-email', 'internal-dashboard']
    ),
    'request_external_transfer': AllowedAction(
        name='request_external_transfer',
        description='Request data transfer to external party',
        required_permissions=['request_external_transfer'],
        data_sensitivity='high',
        allowed_targets=['approved-analytics-service']
    ),
}

TRUSTED_TARGETS = {
    'approved-internal-analytics': {'trust_level': 'high', 'type': 'internal'},
    'approved-analytics-service': {'trust_level': 'medium', 'type': 'approved_external'},
    'internal-dashboard': {'trust_level': 'high', 'type': 'internal'},
    'internal-email': {'trust_level': 'high', 'type': 'internal'},
}

UNTRUSTED_PATTERNS = ['public', 'unauthorized', 'unknown', 'new-external']
