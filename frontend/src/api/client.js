import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  makerRecommend: (claimId, action, notes, makerId) => 
    api.post(`/cases/${claimId}/maker-recommend`, null, { params: { action, notes, maker_id: makerId } }),
  checkerSignoff: (claimId, action, notes, checkerId) => 
    api.post(`/cases/${claimId}/checker-signoff`, null, { params: { action, notes, checker_id: checkerId } }),
  getTrail: (claimId) => api.get(`/cases/${claimId}/trail`),
};

export const analyticsApi = {
  benford: () => api.get('/analytics/benford'),
  relatedParties: () => api.get('/analytics/related-parties'),
  sodViolations: () => api.get('/analytics/sod-violations'),
  caseMetrics: () => api.get('/analytics/case-metrics'),
};

export default api;
