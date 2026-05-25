import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface Report {
  id: number;
  title: string;
  report_type: string;
  status: string;
  ai_summary: string | null;
  ai_findings: Record<string, unknown> | null;
  medicines: Array<{ name: string; dosage?: string; frequency?: string }> | null;
  conditions: string[] | null;
  severity: string | null;
  recommendations: string[] | null;
  historical_comparison: Record<string, unknown> | null;
  generated_pdf_url: string | null;
  is_saved: boolean;
  created_at: string;
}

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    api.post('/auth/register', { email, password, full_name }),
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    return api.post('/auth/login', form, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
  },
  me: () => api.get<User>('/auth/me'),
};

export const uploadApi = {
  analyze: (file: File, saveToHistory: boolean, question?: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('save_to_history', String(saveToHistory));
    if (question) form.append('question', question);
    return api.post('/upload/analyze', form);
  },
  listReports: (savedOnly = false) =>
    api.get<{ reports: Report[]; total: number }>('/upload/reports', {
      params: savedOnly ? { saved_only: true } : {},
    }),
};

export const reportsApi = {
  get: (id: number) => api.get<Report>(`/reports/${id}`),
  compare: (reportIdA: number, reportIdB: number) =>
    api.post('/reports/compare', { report_id_a: reportIdA, report_id_b: reportIdB }),
  timeline: () => api.get('/timeline'),
};

export const chatApi = {
  send: (message: string, sessionId?: string, reportId?: number) =>
    api.post('/chat', { message, session_id: sessionId, report_id: reportId }),
  history: (sessionId: string) => api.get(`/chat/${sessionId}`),
};

export function getWsUrl(path: string): string {
  const wsBase =
    import.meta.env.VITE_WS_URL ||
    (import.meta.env.DEV ? 'ws://localhost:8000' : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`);
  return `${wsBase}${path}`;
}
