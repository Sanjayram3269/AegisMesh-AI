# AegisMesh AI — API Contract

## Overview
This document specifies the REST API contract for interacting with the AegisMesh AI governance layer.

## HTTP Status Codes
- `200 OK`: Request successful.
- `201 Created`: Resource (e.g., audit record) successfully created.
- `400 Bad Request`: Invalid input format or missing fields.
- `401 Unauthorized`: Missing or invalid authentication token.
- `403 Forbidden`: Insufficient permissions.
- `404 Not Found`: Resource not found.
- `500 Internal Server Error`: Unexpected system failure.

## Endpoints

### 1. Evaluate Governance Request
`POST /api/govern`

**Request Schema:**
```json
{
  "request_id": "req-12345",
  "user": {
    "id": "u-987",
    "role": "Data Analyst",
    "department": "Marketing"
  },
  "action": "export",
  "target": "customer_demographics_q3",
  "context": {
    "environment": "production",
    "destination": "external_vendor_s3"
  }
}
```

**Response Schema:**
```json
{
  "request_id": "req-12345",
  "decision": "ESCALATE",
  "reasoning": "Exporting customer demographics to an external vendor requires manual review due to PII risk.",
  "risk_score": 85,
  "status": "pending_human_review"
}
```

### 2. System Health Check
`GET /api/health`

**Response Schema:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "up",
    "llm_provider": "up",
    "rag_service": "up"
  }
}
```

### 3. List Audit Records
`GET /api/audit`

**Query Parameters:**
- `page` (int, default 1)
- `limit` (int, default 20)
- `status` (string, optional)

**Response Schema:**
```json
{
  "data": [
    {
      "request_id": "req-12345",
      "timestamp": "2026-08-08T12:00:00Z",
      "decision": "ESCALATE",
      "user_id": "u-987"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "limit": 20
  }
}
```

### 4. Get Audit Record Details
`GET /api/audit/{request_id}`

**Response Schema:**
```json
{
  "request_id": "req-12345",
  "timestamp": "2026-08-08T12:00:00Z",
  "request_payload": {
    "action": "export",
    "target": "customer_demographics_q3"
  },
  "agent_traces": [
    {
      "agent": "Compliance",
      "status": "completed",
      "output": "Policy Data_Handling_01 violated."
    }
  ],
  "final_decision": "ESCALATE",
  "reviewer_notes": null
}
```

### 5. Human Review Action
`POST /api/review/{request_id}`

**Request Schema:**
```json
{
  "action": "approve", 
  "reviewer_id": "admin-1",
  "comments": "Approved after verifying vendor NDA."
}
```

**Response Schema:**
```json
{
  "request_id": "req-12345",
  "status": "resolved",
  "final_decision": "APPROVE"
}
```
