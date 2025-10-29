// Simple hash function to generate User ID from phone number
function generateUserId(phoneNumber) {
    let hash = 0;
    for (let i = 0; i < phoneNumber.length; i++) {
        const char = phoneNumber.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).toUpperCase(); // Convert to hexadecimal
}

// No-op submit handler (prevents form submit when pressing Enter)
function handleSubmit(event) {
    event.preventDefault();
}

// LocalStorage user store helpers
const STORAGE_KEY = 'geo_users';

function loadUsers() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch (e) {
        return {};
    }
}

function saveUsers(users) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
}

// Display message to user
function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
}

// Handle login
function handleLogin(event) {
    event.preventDefault();

    const input = document.getElementById('userId').value.trim();
    const password = document.getElementById('password').value;

    if (!input || !password) {
        showMessage('Please enter both User ID (or phone number) and password', 'error');
        return;
    }

    const users = loadUsers();

    // If input looks like a 10-digit phone number, convert to userId first
    let userId = input;
    if (/^\d{10}$/.test(input)) {
        userId = generateUserId(input);
    }

    const user = users[userId];
    if (!user) {
        // User ID not found
        showMessage('User ID not found — please sign up first', 'error');
        return;
    }

    if (user.password !== password) {
        showMessage('Incorrect password', 'error');
        return;
    }

    showMessage(`Logged in successfully with User ID: ${userId}`, 'success');
}

// Handle signup
function handleSignup(event) {
    event.preventDefault();

    const phoneInput = document.getElementById('userId').value.trim();
    const password = document.getElementById('password').value;

    if (!/^\d{10}$/.test(phoneInput)) {
        showMessage('Please enter a valid 10-digit phone number to sign up', 'error');
        return;
    }

    if (!password) {
        showMessage('Please enter a password', 'error');
        return;
    }

    const users = loadUsers();
    const userId = generateUserId(phoneInput);

    if (users[userId]) {
        showMessage(`Account already exists. Your User ID is: ${userId}`, 'error');
        return;
    }

    // Create user
    users[userId] = {
        phone: phoneInput,
        password: password
    };
    saveUsers(users);

    // Update the User ID field to the generated ID so the user sees it
    document.getElementById('userId').value = userId;

    showMessage(`Account created successfully! Your User ID is: ${userId}`, 'success');
}