import { GovernRequest, GovernResponse, HealthResponse, AuditRecord } from '../types';

const API_BASE_URL = '/api';

export const api = {
  async governAction(request: GovernRequest): Promise<GovernResponse> {
    const response = await fetch(`${API_BASE_URL}/govern`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error('Failed to govern action');
    }
    return response.json();
  },

  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error('Failed to fetch health status');
    }
    return response.json();
  },

  async getAuditRecords(): Promise<{ total: number; records: AuditRecord[] }> {
    const response = await fetch(`${API_BASE_URL}/audit`);
    if (!response.ok) {
      throw new Error('Failed to fetch audit records');
    }
    return response.json();
  },

  async submitHumanReview(requestId: string, action: 'approve' | 'reject' | 'request_modification', comments: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/review/${requestId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ action, comments }),
    });
    if (!response.ok) {
      throw new Error('Failed to submit human review');
    }
    return response.json();
  },
};
