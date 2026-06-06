async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const alertMsg = document.getElementById('alert-msg');
    const btnSubmit = document.getElementById('btn-submit');

    // Hide previous alerts
    alertMsg.style.display = 'none';

    // Disable button & loading feedback
    const originalText = btnSubmit.innerHTML;
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<span>Signing In...</span> <i class="fas fa-spinner fa-spin"></i>';

    try {
        await api.login(username, password);
        
        // Flash success
        alertMsg.className = 'alert-message alert-success';
        alertMsg.textContent = 'Login successful! Entering dashboard...';
        alertMsg.style.display = 'block';

        setTimeout(() => {
            window.location.href = 'interface.html';
        }, 1000);

    } catch (err) {
        // Show error message
        alertMsg.className = 'alert-message alert-error';
        alertMsg.textContent = err.message || 'Login failed. Please verify credentials.';
        alertMsg.style.display = 'block';
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = originalText;
    }
}