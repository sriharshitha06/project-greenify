// Greenify Frontend API Handler
const API_BASE_URL = 'http://127.0.0.1:8000';

class GreenifyAPI {
    constructor() {
        this.tokenKey = 'greenify_jwt_token';
    }

    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    setToken(token) {
        localStorage.setItem(this.tokenKey, token);
    }

    removeToken() {
        localStorage.removeItem(this.tokenKey);
    }

    isLoggedIn() {
        return !!this.getToken();
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const token = this.getToken();

        // Setup headers
        const headers = options.headers || {};
        if (token && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Handle JSON bodies automatically
        let body = options.body;
        if (body && typeof body === 'object' && !(body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            body = JSON.stringify(body);
        }

        const fetchOptions = {
            ...options,
            headers,
            body
        };

        try {
            const response = await fetch(url, fetchOptions);
            
            // Check for unauthorized errors and force log out
            if (response.status === 401 && !options.skipAuth) {
                this.removeToken();
                window.location.href = 'login.html';
                throw new Error('Session expired. Please log in again.');
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Request failed with status ${response.status}`);
            }

            // If it's a file download, return blob
            if (headers['Accept'] === 'text/csv' || endpoint.includes('download')) {
                return await response.blob();
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // AUTH Endpoints
    async register(username, email, password) {
        return this.request('/api/auth/register', {
            method: 'POST',
            body: { username, email, password },
            skipAuth: true
        });
    }

    async login(username, password) {
        // We use the JSON login endpoint we built specifically for frontend ease
        const data = await this.request('/api/auth/login-json', {
            method: 'POST',
            body: { username, password },
            skipAuth: true
        });
        if (data && data.access_token) {
            this.setToken(data.access_token);
        }
        return data;
    }

    async getMe() {
        return this.request('/api/auth/me');
    }

    // CARBON FOOTPRINT Endpoints
    async predictCarbon(activityData) {
        return this.request('/api/carbon/predict', {
            method: 'POST',
            body: activityData
        });
    }

    async logActivity(activityData) {
        return this.request('/api/carbon/log', {
            method: 'POST',
            body: activityData
        });
    }

    async getHistory() {
        return this.request('/api/carbon/history');
    }

    async getAnalytics() {
        return this.request('/api/carbon/analytics');
    }

    async downloadReport() {
        const blob = await this.request('/api/carbon/download-report');
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `greenify_carbon_report_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    // IMAGE VERIFICATION Endpoints
    async uploadImage(file, activityType) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('activity_type', activityType);

        return this.request('/api/verify/upload', {
            method: 'POST',
            body: formData
        });
    }

    async getVerifyHistory() {
        return this.request('/api/verify/history');
    }

    // GAMIFICATION Endpoints
    async getLeaderboard() {
        return this.request('/api/gamification/leaderboard');
    }

    async getBadges() {
        return this.request('/api/gamification/badges');
    }

    async checkBadges() {
        return this.request('/api/gamification/check-badges', {
            method: 'POST'
        });
    }

    // RAG RECOMMENDATIONS Endpoints
    async getRecommendations(query = null) {
        let endpoint = '/api/recommendations/get';
        if (query) {
            endpoint += `?query=${encodeURIComponent(query)}`;
        }
        return this.request(endpoint);
    }

    logout() {
        this.removeToken();
        window.location.href = 'login.html';
    }
}

// Global API instance
const api = new GreenifyAPI();
