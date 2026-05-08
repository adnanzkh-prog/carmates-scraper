// frontend/lib/api.js — FIXED VERSION
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://renewed-adventure-production-fef0.up.railway.app';

const api = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
});

// ─── NEW API: Asynchronous Celery Scrape ───
export const startScrape = async (scrapeRequest) => {
    // scrapeRequest = { query, location, min_price, max_price, min_year, max_year, condition, limit, email, password }
    const { data } = await api.post('/scrape', scrapeRequest);
    return data; // { task_id, status: "queued" }
};

export const getScrapeStatus = async (taskId) => {
    const { data } = await api.get(`/scrape/status/${taskId}`);
    return data; // { task_id, status, result }
};

// ─── NEW API: Synchronous Scrape (for testing) ───
export const scrapeSync = async (scrapeRequest) => {
    const { data } = await api.post('/scrape/sync', scrapeRequest);
    return data; // { stored: count }
};

// ─── NEW API: Retrieve Listings from Database ───
export const getListings = async (filters = {}) => {
    const { data } = await api.get('/listings', { params: filters });
    return data; // { total, listings: [...] }
};

// ─── NEW API: Export ───
export const exportCSV = () => {
    window.open(`${API_URL}/export/csv`, '_blank');
};

export const exportExcel = () => {
    window.open(`${API_URL}/export/excel`, '_blank');
};

// ─── Health Check (updated endpoint) ───
export const healthCheck = async () => {
    // Use /listings with limit=1 as health probe since /health was removed
    const { data } = await api.get('/listings?limit=1', { timeout: 5000 });
    return { status: 'ok', total: data.total };
};

export default api;