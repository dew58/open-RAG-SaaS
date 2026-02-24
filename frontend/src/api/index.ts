import { api } from '../lib/axios';

export const documentApi = {
    upload: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/documents/upload', formData, { timeout: 120000 });
    },
    list: () => api.get('/documents').then(res => res.data.items ?? []),
    delete: (id: string) => api.delete(`/documents/${id}`), 
};

export const chatApi = {
    question: (query: string) => api.post('/chat/query', { question: query }),
    history: (page = 1, pageSize = 50) => api.get(`/chat/history?page=${page}&page_size=${pageSize}`),
};

export const clientApi = {
    me: () => api.get('/clients/me'),
    listKeys: () => api.get('/clients/api-keys'),
    generateKey: (name: string) => api.post('/clients/api-keys', { name }),
};

export const exportApi = {
    queries: () => api.get('/export/queries', { responseType: 'blob' }),
};
