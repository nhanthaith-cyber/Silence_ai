import axios from 'axios';

const api = axios.create({
  headers: { 'Content-Type': 'application/json' },
});

// Conversations
export const getConversations = (params?: {
  platform?: string;
  status?: string;
  search?: string;
}) => api.get('/api/conversations', { params }).then(r => r.data);

export const getConversation = (id: string) =>
  api.get(`/api/conversations/${id}`).then(r => r.data);

export const getMessages = (conversationId: string) =>
  api.get(`/api/conversations/${conversationId}/messages`).then(r => r.data);

export const sendMessage = (id: string, content: string, imageBase64?: string) =>
  api.post(`/api/conversations/${id}/messages`, { content, image_base64: imageBase64 }).then(r => r.data);

export const sendMockInboundMessage = (id: string, content: string, imageBase64?: string) =>
  api.post(`/api/conversations/${id}/mock-inbound`, { content, image_base64: imageBase64 }).then(r => r.data);

export const handoffConversation = (conversationId: string, agentName: string, note?: string) =>
  api.post(`/api/conversations/${conversationId}/handoff`, { agent_name: agentName, note }).then(r => r.data);

export const resolveConversation = (conversationId: string) =>
  api.patch(`/api/conversations/${conversationId}/resolve`).then(r => r.data);

// Knowledge Base
export const getKnowledge = (params?: { category?: string; search?: string }) =>
  api.get('/api/knowledge', { params }).then(r => r.data);

export const createKnowledge = (data: { category: string; question: string; answer: string; tags: string; is_active?: boolean }) =>
  api.post('/api/knowledge', data).then(r => r.data);

export const updateKnowledge = (id: string, data: Partial<{ question: string; answer: string; is_active: boolean }>) =>
  api.put(`/api/knowledge/${id}`, data).then(r => r.data);

export const deleteKnowledge = (id: string) =>
  api.delete(`/api/knowledge/${id}`).then(r => r.data);

// Tickets
export const getTickets = (params?: { status?: string; category?: string; priority?: string }) =>
  api.get('/api/tickets', { params }).then(r => r.data);

export const getTicketStats = (category?: string) =>
  api.get('/api/tickets/stats', { params: { category } }).then(r => r.data);

export const updateTicket = (id: string, data: any) =>
  api.patch(`/api/tickets/${id}`, data).then(r => r.data);

// Agent Config
export const getAgentConfigs = () =>
  api.get('/api/agents').then(r => r.data);

export const updateAgentConfig = (id: string, data: object) =>
  api.put(`/api/agents/${id}`, data).then(r => r.data);

// Analytics
export const getAnalyticsOverview = () =>
  api.get('/api/analytics/overview').then(r => r.data);

// Simulations (Mock data)
export const simulateShopeeMock = () =>
  api.post('/webhook/shopee/mock').then(r => r.data);

export const simulateTikTokMock = () =>
  api.post('/webhook/tiktok/mock').then(r => r.data);

export const simulateAll = () =>
  api.post('/webhook/simulate').then(r => r.data);

// Documents (RAG)
export const getDocuments = () =>
  api.get('/api/documents').then(r => r.data);

export const uploadDocument = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data);
};

export const deleteDocument = (id: string) =>
  api.delete(`/api/documents/${id}`).then(r => r.data);

// Memory
export const getCustomerMemory = (customerId: string, platform: string) =>
  api.get(`/api/memory/${platform}/${customerId}`).then(r => r.data);

export const updateCustomerMemory = (customerId: string, platform: string, data: any) =>
  api.post(`/api/memory/${platform}/${customerId}`, data).then(r => r.data);

// Products
export const getProducts = (params?: { category?: string; search?: string }) =>
  api.get('/api/products', { params }).then(r => r.data);

export default api;
