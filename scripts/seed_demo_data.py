#!/usr/bin/env python3
"""Seed demo data for AegisMesh AI demonstration scenarios."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DEMO_SCENARIOS = [
    {
        "id": "DEMO-001",
        "name": "Safe Analytics Export",
        "description": "Export anonymized aggregated customer analytics to approved internal analytics service.",
        "request": {
            "request_id": "REQ-DEMO-001",
            "user_id": "U001",
            "role": "Senior Data Analyst",
            "action": "Export anonymized aggregated customer analytics",
            "target": "approved-internal-analytics",
            "metadata": {"data_type": "aggregated", "pii": False}
        },
        "expected_decision": "APPROVE",
        "expected_risk_level": "LOW",
        "expected_risk_score_range": [5, 25]
    },
    {
        "id": "DEMO-002",
        "name": "PII Data Export",
        "description": "Export customer records containing email and phone numbers to approved analytics service.",
        "request": {
            "request_id": "REQ-DEMO-002",
            "user_id": "U002",
            "role": "Marketing Analyst",
            "action": "Export customer records containing email and phone numbers",
            "target": "approved-analytics-service",
            "metadata": {"data_type": "customer_records", "pii": True}
        },
        "expected_decision": "MODIFY",
        "expected_risk_level": "MEDIUM",
        "expected_risk_score_range": [40, 65]
    },
    {
        "id": "DEMO-003",
        "name": "External Vendor Transfer",
        "description": "Send sensitive customer dataset to a new external analytics vendor.",
        "request": {
            "request_id": "REQ-DEMO-003",
            "user_id": "U003",
            "role": "Marketing Analyst",
            "action": "Send sensitive customer dataset to a new external analytics vendor",
            "target": "new-external-vendor",
            "metadata": {"data_type": "sensitive", "vendor_status": "new"}
        },
        "expected_decision": "ESCALATE",
        "expected_risk_level": "HIGH",
        "expected_risk_score_range": [70, 90]
    },
    {
        "id": "DEMO-004",
        "name": "Unauthorized Public Export",
        "description": "Export confidential customer database to an unauthorized public endpoint.",
        "request": {
            "request_id": "REQ-DEMO-004",
            "user_id": "U004",
            "role": "Junior Analyst",
            "action": "Export confidential customer database to unauthorized public endpoint",
            "target": "public-endpoint-unauthorized",
            "metadata": {"data_type": "confidential", "target_trust": "untrusted"}
        },
        "expected_decision": "REJECT",
        "expected_risk_level": "CRITICAL",
        "expected_risk_score_range": [90, 100]
    }
]

DEMO_USERS = [
    {
        "user_id": "U001",
        "name": "Alice Chen",
        "role": "Senior Data Analyst",
        "department": "Data Analytics",
        "clearance_level": "high",
        "permissions": [
            "read_customer_summary",
            "export_anonymized_report",
            "send_internal_report",
            "request_external_transfer"
        ]
    },
    {
        "user_id": "U002",
        "name": "Bob Martinez",
        "role": "Marketing Analyst",
        "department": "Marketing",
        "clearance_level": "medium",
        "permissions": [
            "read_customer_summary",
            "export_anonymized_report",
            "send_internal_report"
        ]
    },
    {
        "user_id": "U003",
        "name": "Carol Williams",
        "role": "Marketing Analyst",
        "department": "Marketing",
        "clearance_level": "medium",
        "permissions": [
            "read_customer_summary",
            "export_anonymized_report",
            "send_internal_report"
        ]
    },
    {
        "user_id": "U004",
        "name": "Dave Thompson",
        "role": "Junior Analyst",
        "department": "Analytics",
        "clearance_level": "low",
        "permissions": [
            "read_customer_summary"
        ]
    }
]


def main():
    """Print demo scenarios and users for verification."""
    print("=" * 60)
    print("AegisMesh AI — Demo Scenarios")
    print("=" * 60)
    
    for scenario in DEMO_SCENARIOS:
        print(f"\n{'─' * 50}")
        print(f"  {scenario['id']}: {scenario['name']}")
        print(f"  Action: {scenario['request']['action']}")
        print(f"  Target: {scenario['request']['target']}")
        print(f"  Expected: {scenario['expected_decision']} ({scenario['expected_risk_level']})")
    
    print(f"\n{'=' * 60}")
    print("Demo Users")
    print("=" * 60)
    
    for user in DEMO_USERS:
        print(f"\n  {user['user_id']}: {user['name']} — {user['role']}")
        print(f"    Clearance: {user['clearance_level']}")
        print(f"    Permissions: {', '.join(user['permissions'])}")
    
    # Write to JSON for programmatic access
    output = {
        "scenarios": DEMO_SCENARIOS,
        "users": DEMO_USERS
    }
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'rag', 'data', 'demo_scenarios.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nDemo data written to: {output_path}")


if __name__ == '__main__':
    main()
