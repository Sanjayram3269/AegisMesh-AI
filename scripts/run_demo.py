#!/usr/bin/env python3
"""Run AegisMesh AI demo — sends all 4 demo scenarios to the governance API."""

import json
import sys
import time

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

from seed_demo_data import DEMO_SCENARIOS

API_URL = "http://localhost:8000"


def run_demo():
    """Execute all demo scenarios against the running backend."""
    print("\n" + "=" * 60)
    print("  AegisMesh AI — Live Demo")
    print("=" * 60)
    
    # Health check
    try:
        resp = httpx.get(f"{API_URL}/api/health", timeout=5.0)
        health = resp.json()
        print(f"\n  Backend Status: {health.get('status', 'unknown')}")
        print(f"  Provider: {health.get('provider', 'unknown')}")
    except Exception as e:
        print(f"\n  ERROR: Backend not reachable at {API_URL}")
        print(f"  Start the backend first: uvicorn app.main:app --reload")
        sys.exit(1)
    
    results = []
    
    for scenario in DEMO_SCENARIOS:
        print(f"\n{'─' * 60}")
        print(f"  Scenario: {scenario['name']}")
        print(f"  Action: {scenario['request']['action']}")
        print(f"  Target: {scenario['request']['target']}")
        print(f"  Expected: {scenario['expected_decision']}")
        print(f"{'─' * 60}")
        
        try:
            resp = httpx.post(
                f"{API_URL}/api/govern",
                json=scenario['request'],
                timeout=30.0
            )
            result = resp.json()
            
            decision = result.get('decision', 'UNKNOWN')
            risk_score = result.get('risk_score', -1)
            risk_level = result.get('risk_level', 'UNKNOWN')
            
            match = '✓' if decision == scenario['expected_decision'] else '✗'
            
            print(f"  Result: {match} {decision} (Risk: {risk_score} — {risk_level})")
            print(f"  Explanation: {result.get('explanation', 'N/A')[:120]}...")
            
            results.append({
                'scenario': scenario['name'],
                'expected': scenario['expected_decision'],
                'actual': decision,
                'match': decision == scenario['expected_decision']
            })
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'scenario': scenario['name'],
                'expected': scenario['expected_decision'],
                'actual': 'ERROR',
                'match': False
            })
        
        time.sleep(0.5)
    
    # Summary
    print(f"\n{'=' * 60}")
    print("  Demo Summary")
    print(f"{'=' * 60}")
    
    passed = sum(1 for r in results if r['match'])
    total = len(results)
    
    for r in results:
        status = '✓ PASS' if r['match'] else '✗ FAIL'
        print(f"  {status}: {r['scenario']} — Expected {r['expected']}, Got {r['actual']}")
    
    print(f"\n  Result: {passed}/{total} scenarios passed")
    
    return passed == total


if __name__ == '__main__':
    success = run_demo()
    sys.exit(0 if success else 1)
