import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

const TOKEN_KEY = 'auditai_session_token';
api.interceptors.request.use((request) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) request.headers.Authorization = `Bearer ${token}`;
  return request;
});
api.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
    sessionStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event('auditai:unauthorized'));
  }
  return Promise.reject(error);
});

export const authApi = {
  tokenKey: TOKEN_KEY,
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
};

export const claimsApi = {
  list: (params) => api.get('/claims', { params }),
  getDetail: (claimId) => api.get(`/claims/${claimId}`),
  upload: (formData) => api.post('/claims/upload', formData, { 
    headers: { 'Content-Type': 'multipart/form-data' } 
  }),
  uploadReceipt: (claimId, formData) => api.post(`/receipts/upload?claim_id=${claimId}`, formData, { 
    headers: { 'Content-Type': 'multipart/form-data' } 
  }),
};

export const receiptsApi = {
  get: (receiptId) => api.get(`/receipts/${receiptId}`),
};

export const fraudApi = {
  summary: () => api.get('/fraud/summary'),
  score: () => api.post('/fraud/score'),
  train: () => api.post('/fraud/train'),
};

export const reportsApi = {
  generate: (claimId) => api.post(`/reports/generate/${claimId}`),
  generateAll: () => api.post('/reports/generate-all'),
};

export const casesApi = {
  list: (params) => api.get('/cases', { params }),
  makerRecommend: (claimId, action, notes) =>
    api.post(`/cases/${claimId}/maker-recommend`, null, { params: { action, notes } }),
  checkerSignoff: (claimId, action, notes) =>
    api.post(`/cases/${claimId}/checker-signoff`, null, { params: { action, notes } }),
  getTrail: (claimId) => api.get(`/cases/${claimId}/trail`),
};

export const analyticsApi = {
  benford: () => api.get('/analytics/benford'),
  relatedParties: () => api.get('/analytics/related-parties'),
  sodViolations: () => api.get('/analytics/sod-violations'),
  caseMetrics: () => api.get('/analytics/case-metrics'),
};

export default api;
