const API_BASE = '/api';

// Helper function to get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem('authToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

// In auth.js, update the login function to use the new API
async function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.querySelector('input[name="email"]').value;
    const password = form.querySelector('input[name="password"]').value;
    const errorElement = form.querySelector('.error-message');
    const submitButton = form.querySelector('button[type="submit"]');
    
    try {
        // Show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing in...';
        
        // Call the API
        const response = await api.auth.login(email, password, 'customer');
        
        // Store auth data
        localStorage.setItem('authToken', response.token);
        localStorage.setItem('authUser', JSON.stringify(response.user));
        
        // Redirect to home page
        window.location.href = '/index.html';
        
    } catch (error) {
        console.error('Login failed:', error);
        errorElement.textContent = error.message || 'Login failed. Please try again.';
        errorElement.style.display = 'block';
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = 'Sign In';
    }
}

// Handle customer login form submission
async function handleCustomerLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.querySelector('input[name="email"]').value;
    const password = form.querySelector('input[type="password"]').value;
    const errorElement = document.getElementById('login-error');
    const submitButton = form.querySelector('button[type="submit"]');
    const btnText = submitButton.querySelector('.btn-text');
    const btnLoading = submitButton.querySelector('.btn-loading');
    
    try {
        // Show loading state
        submitButton.disabled = true;
        btnText.classList.add('hide');
        btnLoading.style.display = 'inline-block';
        errorElement.style.display = 'none';

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
                role: 'customer'
            })
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed. Please check your credentials.');
        }

        // Store auth data
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('authUser', JSON.stringify(data.user));
        
        // Redirect based on role
        window.location.href = data.user.role === 'farmer' ? 'farmer-dashboard.html' : 'index.html';
        
    } catch (error) {
        console.error('Login error:', error);
        errorElement.textContent = error.message;
        errorElement.style.display = 'block';
    } finally {
        submitButton.disabled = false;
        btnText.classList.remove('hide');
        btnLoading.style.display = 'none';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in
    const authUser = localStorage.getItem('authUser');
    if (authUser) {
        const user = JSON.parse(authUser);
        const redirectUrl = user.role === 'farmer' ? 'farmer-dashboard.html' : 'index.html';
        if (!window.location.pathname.endsWith(redirectUrl)) {
            window.location.href = redirectUrl;
        }
        return;
    }

    // Add login form handler
    const customerLoginForm = document.getElementById('customer-login-form');
    if (customerLoginForm) {
        customerLoginForm.addEventListener('submit', handleCustomerLogin);
    }
});

// Enhanced apiRequest function with auth token
async function apiRequest(path, body, method = 'POST') {
    const response = await fetch(`${API_BASE}${path}`, {
        method,
        headers: getAuthHeaders(),
        body: body ? JSON.stringify(body) : undefined
    });
    
    if (response.status === 401) {
        // Token expired or invalid, clear auth and redirect to login
        localStorage.removeItem('authToken');
        localStorage.removeItem('authUser');
        window.location.href = 'login.html';
        throw new Error('Session expired. Please login again.');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Request failed');
    }
    return response.json();
}

// Function to check authentication state
function checkAuth() {
    const token = localStorage.getItem('authToken');
    const user = JSON.parse(localStorage.getItem('authUser') || 'null');
    const currentPath = window.location.pathname;
    
    console.log('Current path:', currentPath);
    console.log('Token exists:', !!token);
    console.log('User exists:', !!user);
    
    // Only redirect if we're not already on the target page
    const isOnLoginPage = currentPath.endsWith('login.html') || currentPath.endsWith('login');
    const isOnSignupPage = currentPath.endsWith('signup.html') || currentPath.endsWith('signup');
    const isOnIndexPage = currentPath.endsWith('index.html') || currentPath.endsWith('/');
    
    // If user is already logged in and trying to access login/signup, redirect to home
    if ((isOnLoginPage || isOnSignupPage) && token && user) {
        if (!isOnIndexPage) {
            console.log('Already logged in, redirecting to index');
            window.location.href = 'index.html';
            return false;
        }
    }
    
    // List of public pages that don't require authentication
    const publicPages = ['login.html', 'signup.html', 'index.html', '/', ''];
    const isPublicPage = publicPages.some(page => currentPath.endsWith(page));
    
    // If not on a public page and not logged in, redirect to login
    if (!isPublicPage && !token) {
        console.log('Not logged in, redirecting to login');
        window.location.href = 'login.html';
        return false;
    }
    
    return { token, user };
}

// Handle successful login
function handleLoginSuccess(data) {
    if (!data || !data.user || !data.token) {
        console.error('Invalid login response:', data);
        throw new Error('Invalid server response');
    }
    
    console.log('Login successful, user:', data.user);
    
    // Store auth data
    localStorage.setItem('authUser', JSON.stringify(data.user));
    localStorage.setItem('authToken', data.token);
    
    // Redirect based on user role
    const redirectUrl = data.user.role === 'farmer' ? 'farmer-dashboard.html' : 'index.html';
    console.log('Redirecting to:', redirectUrl);
    window.location.href = redirectUrl;
}

function attachSignupHandlers() {
    const customerForm = document.querySelector('#customer-form form');
    const farmerForm = document.querySelector('#farmer-form form');

    if (customerForm) {
        customerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const firstName = customerForm.querySelector('#customer-firstname').value.trim();
            const lastName = customerForm.querySelector('#customer-lastname').value.trim();
            const email = customerForm.querySelector('#customer-email').value.trim();
            const password = customerForm.querySelector('#customer-password').value;
            const confirmPassword = customerForm.querySelector('#customer-confirm-password').value;

            if (!firstName || !lastName || !email || !password || !confirmPassword) {
                alert('Please fill in all fields');
                return;
            }

            if (password !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }

            try {
                const response = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        first_name: firstName,
                        last_name: lastName,
                        email: email,
                        password: password,
                        role: 'customer'
                    })
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Signup failed');
                }

                alert('Account created successfully! Please login.');
                window.location.href = 'login.html';
            } catch (error) {
                console.error('Signup error:', error);
                alert(error.message || 'Signup failed. Please try again.');
            }
        });
    }

    if (farmerForm) {
        farmerForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const firstName = farmerForm.querySelector('#farmer-firstname').value.trim();
            const lastName = farmerForm.querySelector('#farmer-lastname').value.trim();
            const email = farmerForm.querySelector('#farmer-email').value.trim();
            const password = farmerForm.querySelector('#farmer-password').value;
            const confirmPassword = farmerForm.querySelector('#farmer-confirm-password').value;
            const farmName = farmerForm.querySelector('#farm-name').value.trim();
            const farmLocation = farmerForm.querySelector('#farm-location').value.trim();
            const primaryProducts = farmerForm.querySelector('#farm-type').value.trim();

            if (!firstName || !lastName || !email || !password || !confirmPassword || !farmName || !farmLocation || !primaryProducts) {
                alert('Please fill in all fields');
                return;
            }

            if (password !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            try {
                const response = await fetch('/api/auth/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        first_name: firstName,
                        last_name: lastName,
                        email: email,
                        password: password,
                        role: 'farmer',
                        farmer_profile: {
                            farm_name: farmName,
                            farm_location: farmLocation,
                            primary_products: primaryProducts
                        }
                    })
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Signup failed');
                }

                alert('Farmer account created successfully! Please login.');
                window.location.href = 'login.html';
            } catch (error) {
                console.error('Signup error:', error);
                alert(error.message || 'Signup failed. Please try again.');
            }
        });
    }
}

function attachLoginHandlers() {
    const customerLoginForm = document.querySelector('#customer-form form');
    const farmerLoginForm = document.querySelector('#farmer-form form');

    if (customerLoginForm) {
        customerLoginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const email = customerLoginForm.querySelector('#customer-email').value.trim();
            const password = customerLoginForm.querySelector('#customer-password').value;
            
            if (!email || !password) {
                alert('Please fill in all fields');
                return;
            }

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password,
                        role: 'customer'
                    })
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Login failed');
                }

                handleLoginSuccess(data);
            } catch (error) {
                console.error('Login error:', error);
                alert(error.message || 'Login failed. Please try again.');
            }
        });
    }

    if (farmerLoginForm) {
        farmerLoginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const email = farmerLoginForm.querySelector('#farmer-email').value.trim();
            const password = farmerLoginForm.querySelector('#farmer-password').value;
            
            if (!email || !password) {
                alert('Please fill in all fields');
                return;
            }

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password,
                        role: 'farmer'
                    })
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Login failed');
                }

                handleLoginSuccess(data);
            } catch (error) {
                console.error('Login error:', error);
                alert(error.message || 'Login failed. Please try again.');
            }
        });
    }
}

// Logout function
function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    window.location.href = 'login.html';
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing auth...');
    
    // Check authentication state on page load
    const auth = checkAuth();
    
    // Always attach handlers if the forms exist on the page
    const currentPath = window.location.pathname;
    console.log('Current path for handler attachment:', currentPath);
    
    if (document.querySelector('#customer-form form') || document.querySelector('#farmer-form form')) {
        console.log('Attaching login/signup handlers');
        if (currentPath.includes('login')) {
            console.log('Attaching login handlers');
            attachLoginHandlers();
        } else if (currentPath.includes('signup')) {
            console.log('Attaching signup handlers');
            attachSignupHandlers();
        } else {
            // Try to attach both handlers if we can't determine the page type
            attachLoginHandlers();
            attachSignupHandlers();
        }
    }
    
    // Update UI based on auth state
    const loginLinks = document.querySelectorAll('.nav-link[href="login.html"]');
    const logoutLinks = document.querySelectorAll('.logout-link');
    const userProfile = document.querySelector('.user-profile');
    const userName = document.querySelector('.user-name');
    
    if (auth && auth.user) {
        // User is logged in
        loginLinks.forEach(link => link.style.display = 'none');
        logoutLinks.forEach(link => {
            link.style.display = 'block';
            link.addEventListener('click', (e) => {
                e.preventDefault();
                logout();
            });
        });
        
        if (userProfile) userProfile.style.display = 'flex';
        if (userName) userName.textContent = JSON.parse(localStorage.getItem('authUser')).first_name;
    } else {
        // User is not logged in
        loginLinks.forEach(link => link.style.display = 'block');
        logoutLinks.forEach(link => link.style.display = 'none');
        if (userProfile) userProfile.style.display = 'none';
    }

    // Attach form handlers
    attachSignupHandlers();
    attachLoginHandlers();
});

