// api.js
const API_BASE = '/api';

async function apiRequest(endpoint, method = 'GET', data = null, requireAuth = true) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
    };

    // Add auth token if required
    if (requireAuth) {
        const token = localStorage.getItem('authToken');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }

    const config = {
        method,
        headers,
        credentials: 'same-origin'
    };

    if (data) {
        config.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, config);
        const responseData = await response.json();

        if (!response.ok) {
            // Handle 401 Unauthorized
            if (response.status === 401) {
                localStorage.removeItem('authToken');
                localStorage.removeItem('authUser');
                window.location.href = `/login.html?redirect=${encodeURIComponent(window.location.pathname)}`;
            }
            throw new Error(responseData.detail || 'An error occurred');
        }

        return responseData;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Auth API
export const auth = {
    login: async (email, password, role) => {
        return apiRequest('/auth/login', 'POST', { email, password, role }, false);
    },
    signup: async (userData) => {
        return apiRequest('/auth/signup', 'POST', userData, false);
    },
    getProfile: async () => {
        return apiRequest('/auth/me');
    }
};

// Products API
export const products = {
    getAll: async () => {
        return apiRequest('/products');
    },
    getById: async (id) => {
        return apiRequest(`/products/${id}`);
    }
};

// Cart API
export const cart = {
    get: async () => {
        return apiRequest('/cart');
    },
    addItem: async (productId, quantity = 1) => {
        return apiRequest('/cart/items', 'POST', { productId, quantity });
    },
    updateItem: async (itemId, quantity) => {
        return apiRequest(`/cart/items/${itemId}`, 'PUT', { quantity });
    },
    removeItem: async (itemId) => {
        return apiRequest(`/cart/items/${itemId}`, 'DELETE');
    },
    clear: async () => {
        return apiRequest('/cart', 'DELETE');
    }
};

// Export for browser
window.api = { auth, products, cart };