const API_BASE = '/api';

// Helper function to get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem('authToken');
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}

// Main API request function with authentication
async function fetchWithAuth(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers: {
                ...getAuthHeaders(),
                ...(options.headers || {})
            },
            credentials: 'include', // Include cookies for session handling
            mode: 'cors', // Enable CORS
            body: options.body ? JSON.stringify(options.body) : undefined
        });

        if (response.status === 401) {
            // Token expired or invalid, clear auth and redirect to login
            localStorage.removeItem('authToken');
            localStorage.removeItem('authUser');
            window.location.href = 'login.html';
            return Promise.reject(new Error('Session expired. Please login again.'));
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.message || 'Request failed');
        }

        // Handle empty responses
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return null;
        }

        return response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// API Functions
const api = {
    // Auth
    login: (email, password, role) => 
        fetchWithAuth('/auth/login', {
            method: 'POST',
            body: { email, password, role }
        }),

    signup: (userData) => 
        fetchWithAuth('/auth/signup', {
            method: 'POST',
            body: userData
        }),

    // Products
    getProducts: () => 
        fetchWithAuth('/products', { method: 'GET' }),

    getProduct: (id) => 
        fetchWithAuth(`/products/${id}`, { method: 'GET' }),

    // Cart
    getCart: () => 
        fetchWithAuth('/cart', { method: 'GET' }),

    addToCart: (productId, quantity = 1) => 
        fetchWithAuth('/cart/items', {
            method: 'POST',
            body: { product_id: productId, quantity }
        }),

    removeFromCart: (itemId) => 
        fetchWithAuth(`/cart/items/${itemId}`, {
            method: 'DELETE'
        }),

    // Orders
    createOrder: (orderData) => 
        fetchWithAuth('/orders', {
            method: 'POST',
            body: orderData
        }),

    getOrders: () => 
        fetchWithAuth('/orders', { method: 'GET' }),

    // Profile
    getProfile: () => 
        fetchWithAuth('/profile', { method: 'GET' }),

    updateProfile: (profileData) => 
        fetchWithAuth('/profile', {
            method: 'PUT',
            body: profileData
        })
};

// Make API available globally
window.api = api;
