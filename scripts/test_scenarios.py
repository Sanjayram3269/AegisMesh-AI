"""Test all 4 demo scenarios against the running backend."""
import sys
try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

API_URL = "http://localhost:8000"

scenarios = [
    {
        "name": "APPROVE",
        "data": {
            "request_id": "REQ-DEMO-001",
            "user_id": "U001",
            "role": "Senior Data Analyst",
            "action": "Export anonymized aggregated customer analytics",
            "target": "approved-internal-analytics",
            "metadata": {}
        }
    },
    {
        "name": "MODIFY",
        "data": {
            "request_id": "REQ-DEMO-002",
            "user_id": "U002",
            "role": "Marketing Analyst",
            "action": "Export customer records containing email and phone numbers",
            "target": "approved-analytics-service",
            "metadata": {}
        }
    },
    {
        "name": "ESCALATE",
        "data": {
            "request_id": "REQ-DEMO-003",
            "user_id": "U003",
            "role": "Marketing Analyst",
            "action": "Send sensitive customer dataset to a new external analytics vendor",
            "target": "new-external-vendor",
            "metadata": {}
        }
    },
    {
        "name": "REJECT",
        "data": {
            "request_id": "REQ-DEMO-004",
            "user_id": "U004",
            "role": "Junior Analyst",
            "action": "Export confidential customer database to unauthorized public endpoint",
            "target": "public-endpoint-unauthorized",
            "metadata": {}
        }
    },
]

def main():
    # Health check
    try:
        r = httpx.get(f"{API_URL}/api/health", timeout=5.0)
        h = r.json()
        print(f"Backend: {h['status']} | Provider: {h['provider']} | Demo: {h['demo_mode']}")
    except Exception as e:
        print(f"Backend not reachable: {e}")
        sys.exit(1)

    results = []
    for s in scenarios:
        print(f"\n{'=' * 60}")
        print(f"  Scenario: {s['name']}")
        print(f"  Action:   {s['data']['action']}")
        print(f"  Target:   {s['data']['target']}")
        print(f"  User:     {s['data']['user_id']} ({s['data']['role']})")
        print(f"{'=' * 60}")

        try:
            r = httpx.post(f"{API_URL}/api/govern", json=s["data"], timeout=30.0)
            if r.status_code == 200:
                result = r.json()
                decision = result.get("decision", "N/A")
                risk_score = result.get("risk_score", "N/A")
                risk_level = result.get("risk_level", "N/A")
                explanation = result.get("explanation", "N/A")
                if len(explanation) > 150:
                    explanation = explanation[:150] + "..."

                match = decision == s["name"]
                status = "PASS" if match else "FAIL"

                print(f"  Decision:    {decision}")
                print(f"  Risk Score:  {risk_score}")
                print(f"  Risk Level:  {risk_level}")
                print(f"  Explanation: {explanation}")
                print(f"  Result:      {status}")

                results.append({"scenario": s["name"], "decision": decision, "match": match})
            else:
                print(f"  ERROR {r.status_code}: {r.text[:300]}")
                results.append({"scenario": s["name"], "decision": "ERROR", "match": False})
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"scenario": s["name"], "decision": "ERROR", "match": False})

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    passed = sum(1 for r in results if r["match"])
    for r in results:
        icon = "PASS" if r["match"] else "FAIL"
        print(f"  {icon}: {r['scenario']} -> {r['decision']}")
    print(f"\n  Total: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
