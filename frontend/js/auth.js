/* Authentication helper functions */

function getToken() {
    return localStorage.getItem('token');
}

function isAuthenticated() {
    const token = getToken();
    if (!token) return false;
    
    try {
        // Check if token is expired
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000; // Convert to milliseconds
        if (Date.now() >= exp) {
            localStorage.removeItem('token');
            return false;
        }
        return true;
    } catch (e) {
        return false;
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

function getAuthHeaders() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// Check auth on page load - ONLY for protected pages
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    console.log('🔐 Auth check - Path:', currentPath);
    console.log('🔐 Is authenticated:', isAuthenticated());
    
    // Skip auth check for login page
    if (currentPath === '/login') {
        console.log('🔐 On login page - skipping auth check');
        return;
    }
    
    // For all other pages, check authentication
    if (!isAuthenticated()) {
        console.log('🔐 Not authenticated - redirecting to login');
        window.location.href = '/login';
    } else {
        console.log('🔐 User is authenticated');
    }
});
