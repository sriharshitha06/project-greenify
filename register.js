async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;
    const alertMsg = document.getElementById('alert-msg');
    const btnSubmit = document.getElementById('btn-submit');

    // Hide previous alerts
    alertMsg.style.display = 'none';

    // Validation checks
    if (password !== confirmPassword) {
        alertMsg.textContent = 'Passwords do not match!';
        alertMsg.style.display = 'block';
        return;
    }

    // Disable button & loading feedback
    const originalText = btnSubmit.innerHTML;
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<span>Creating Account...</span> <i class="fas fa-spinner fa-spin"></i>';

    try {
        await api.register(username, email, password);
        
        // Flash success
        alertMsg.className = 'alert-message alert-success';
        alertMsg.textContent = 'Registration successful! Redirecting to login...';
        alertMsg.style.display = 'block';

        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);

    } catch (err) {
        // Show error message
        alertMsg.className = 'alert-message alert-error';
        alertMsg.textContent = err.message || 'Registration failed. Please try again.';
        alertMsg.style.display = 'block';
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = originalText;
    }
}