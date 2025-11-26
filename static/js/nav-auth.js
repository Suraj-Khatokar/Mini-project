// nav-auth.js
document.addEventListener('DOMContentLoaded', function() {
    updateAuthUI();
    setupEventListeners();
    checkAuthState();
});

function updateAuthUI() {
    const authUser = JSON.parse(localStorage.getItem('authUser') || 'null');
    const authButtons = document.querySelector('.auth-buttons');
    const userMenu = document.getElementById('user-menu');
    
    if (authUser) {
        // User is logged in
        if (authButtons) authButtons.style.display = 'none';
        if (userMenu) {
            userMenu.style.display = 'flex';
            const userName = userMenu.querySelector('.user-name');
            if (userName) {
                userName.textContent = `${authUser.first_name || 'User'}`;
            }
        }
    } else {
        // User is not logged in
        if (authButtons) authButtons.style.display = 'flex';
        if (userMenu) userMenu.style.display = 'none';
    }
}

function setupEventListeners() {
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }

    // User dropdown menu
    const userBtn = document.querySelector('.user-btn');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    
    if (userBtn && dropdownMenu) {
        userBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            dropdownMenu.style.display = 'none';
        });

        // Prevent dropdown from closing when clicking inside
        dropdownMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

function checkAuthState() {
    const authRequired = document.body.hasAttribute('data-auth-required');
    const authUser = JSON.parse(localStorage.getItem('authUser') || 'null');
    
    // Redirect to login if auth is required but user is not logged in
    if (authRequired && !authUser) {
        window.location.href = 'login.html?redirect=' + encodeURIComponent(window.location.pathname);
        return;
    }
    
    // Redirect to appropriate dashboard if user is logged in
    if (authUser) {
        const currentPage = window.location.pathname.split('/').pop();
        const isAuthPage = ['login.html', 'signup.html'].includes(currentPage);
        
        if (isAuthPage) {
            const redirectUrl = authUser.role === 'farmer' ? 'farmer-dashboard.html' : 'index.html';
            window.location.href = redirectUrl;
        }
    }
}

function logout() {
    // Clear auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    
    // Redirect to login page
    window.location.href = 'login.html';
}

// Make functions available globally
window.auth = {
    isAuthenticated: function() {
        return !!localStorage.getItem('authToken');
    },
    getUser: function() {
        return JSON.parse(localStorage.getItem('authUser') || 'null');
    },
    logout: logout
};
