// ==============================================================================
// Coreteron Instagram Suite - Interactive Frontend Logic
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initRandomizer();
    initRegistrationForm();
    initBatchForm();
    initLoginForm();
    initMailboxTest();
    initHumanAction();
    initSSEStream();
});

// ---------------------------------------------------------------------------
// Navigation Tabs
// ---------------------------------------------------------------------------
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navItems.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');

            navItems.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add('active');
        });
    });
}

// ---------------------------------------------------------------------------
// Credentials Randomizer
// ---------------------------------------------------------------------------
function initRandomizer() {
    const btn = document.getElementById('btn-quick-randomize');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        try {
            btn.disabled = true;
            const res = await fetch('/api/generate-credentials');
            const data = await res.json();
            if (data.success && data.data) {
                document.getElementById('reg-username').value = data.data.username;
                document.getElementById('reg-fullname').value = data.data.full_name;
                document.getElementById('reg-password').value = data.data.password;
                document.getElementById('reg-birthday').value = data.data.birthday;
                addLogEntry('info', 'Profile Randomized', `Generated: @${data.data.username}`);
            }
        } catch (e) {
            console.error('Failed to generate credentials:', e);
        } finally {
            btn.disabled = false;
        }
    });
}

// ---------------------------------------------------------------------------
// Registration Form
// ---------------------------------------------------------------------------
function initRegistrationForm() {
    const form = document.getElementById('form-register');
    const submitBtn = document.getElementById('btn-start-register');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            email: document.getElementById('reg-email').value.trim(),
            email_password: document.getElementById('reg-email-password').value.trim(),
            username: document.getElementById('reg-username').value.trim(),
            full_name: document.getElementById('reg-fullname').value.trim(),
            password: document.getElementById('reg-password').value.trim(),
            birthday: document.getElementById('reg-birthday').value,
            proxy: document.getElementById('reg-proxy') ? document.getElementById('reg-proxy').value.trim() : '',
            imap_server: document.getElementById('reg-imap-server').value.trim() || 'witcher.mxrouting.net',
            imap_port: parseInt(document.getElementById('reg-imap-port').value, 10) || 993,
            headless: !document.getElementById('reg-visible-browser').checked,
        };

        resetStepper();
        hideResultBox();
        hideHumanAlert();

        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <svg class="spin" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="10"></circle></svg>
            <span>Automation Running...</span>
        `;
        setGlobalStatus(true, 'Running Registration');

        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!data.success) {
                alert('Registration failed to start: ' + data.message);
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>Start Automated Registration</span>`;
                setGlobalStatus(false, 'System Ready');
            }
        } catch (err) {
            alert('Error connecting to backend: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Start Automated Registration</span>`;
            setGlobalStatus(false, 'System Ready');
        }
    });
}

// ---------------------------------------------------------------------------
// Batch Excel Form
// ---------------------------------------------------------------------------
function initBatchForm() {
    const form = document.getElementById('form-batch-upload');
    const submitBtn = document.getElementById('btn-start-batch');
    const statusBox = document.getElementById('batch-upload-status');
    const fileInput = document.getElementById('batch-file');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select an Excel file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Processing Batch...</span>`;
        statusBox.style.display = 'none';

        try {
            const res = await fetch('/api/batch-register', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();

            statusBox.style.display = 'block';
            if (data.success) {
                statusBox.className = 'alert-box success';
                statusBox.innerHTML = `<strong>Started:</strong> ${data.message}`;
                setGlobalStatus(true, 'Running Batch Accounts');
            } else {
                statusBox.className = 'alert-box error';
                statusBox.innerHTML = `<strong>Upload Failed:</strong> ${data.message}`;
            }
        } catch (err) {
            statusBox.style.display = 'block';
            statusBox.className = 'alert-box error';
            statusBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Start Batch Registration</span>`;
        }
    });
}

// ---------------------------------------------------------------------------
// Login Form
// ---------------------------------------------------------------------------
function initLoginForm() {
    const form = document.getElementById('form-login');
    const submitBtn = document.getElementById('btn-start-login');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            username: document.getElementById('login-username').value.trim(),
            password: document.getElementById('login-password').value.trim(),
            email_password: document.getElementById('login-email-pwd').value.trim(),
            proxy: document.getElementById('login-proxy') ? document.getElementById('login-proxy').value.trim() : '',
            headless: !document.getElementById('login-visible-browser').checked,
        };

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Logging in...</span>`;
        setGlobalStatus(true, 'Running Login');

        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!data.success) {
                alert('Login failed: ' + data.message);
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>Login & Verify Session</span>`;
                setGlobalStatus(false, 'System Ready');
            }
        } catch (err) {
            alert('Error connecting to backend: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Login & Verify Session</span>`;
            setGlobalStatus(false, 'System Ready');
        }
    });
}

// ---------------------------------------------------------------------------
// Mailbox Connection Diagnostics
// ---------------------------------------------------------------------------
function initMailboxTest() {
    const form = document.getElementById('form-mailbox-test');
    const submitBtn = document.getElementById('btn-run-mailbox-test');
    const resultBox = document.getElementById('mailbox-test-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            email: document.getElementById('test-email').value.trim(),
            password: document.getElementById('test-password').value.trim(),
            server: document.getElementById('test-server').value.trim() || 'witcher.mxrouting.net',
            port: parseInt(document.getElementById('test-port').value, 10) || 993,
        };

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span>Testing Connection...</span>`;
        resultBox.style.display = 'none';

        try {
            const res = await fetch('/api/test-mailbox', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();

            resultBox.style.display = 'block';
            if (data.success) {
                resultBox.className = 'alert-box success';
                resultBox.innerHTML = `<strong>Success:</strong> ${data.message}`;
            } else {
                resultBox.className = 'alert-box error';
                resultBox.innerHTML = `<strong>Connection Failed:</strong> ${data.message}`;
            }
        } catch (err) {
            resultBox.style.display = 'block';
            resultBox.className = 'alert-box error';
            resultBox.innerHTML = `<strong>Request Error:</strong> ${err.message}`;
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Test IMAP Connection</span>`;
        }
    });
}

// ---------------------------------------------------------------------------
// Human Intervention Signal Button
// ---------------------------------------------------------------------------
function initHumanAction() {
    const doneBtn = document.getElementById('btn-human-done');
    if (!doneBtn) return;

    doneBtn.addEventListener('click', async () => {
        doneBtn.disabled = true;
        try {
            await fetch('/api/human-action', { method: 'POST' });
            hideHumanAlert();
        } catch (e) {
            console.error('Failed to notify human action:', e);
        } finally {
            doneBtn.disabled = false;
        }
    });
}

function showHumanAlert(msg) {
    const alertBox = document.getElementById('human-alert-box');
    const msgEl = document.getElementById('human-alert-message');
    if (msg) msgEl.innerText = msg;
    alertBox.style.display = 'flex';
}

function hideHumanAlert() {
    const alertBox = document.getElementById('human-alert-box');
    if (alertBox) alertBox.style.display = 'none';
}

// ---------------------------------------------------------------------------
// Server-Sent Events (SSE) Stream
// ---------------------------------------------------------------------------
function initSSEStream() {
    const evtSource = new EventSource('/api/logs/stream');

    evtSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            handleIncomingEvent(data);
        } catch (err) {
            // keepalive
        }
    };

    evtSource.onerror = (err) => {
        console.warn('SSE connection issue, retrying...', err);
    };

    document.getElementById('btn-clear-logs').addEventListener('click', () => {
        document.getElementById('console-logs').innerHTML = '';
    });
}

function handleIncomingEvent(event) {
    addLogEntry(event.level || 'info', event.title, event.message, event.timestamp);

    if (event.human_required) {
        showHumanAlert(event.message);
    } else if (event.step === 'human_resume' || event.step === 'completed') {
        hideHumanAlert();
    }

    updateStepper(event.step);

    if (event.step === 'completed' || event.step === 'exception') {
        onTaskFinished(event);
    }
}

function updateStepper(step) {
    const nodes = {
        init: document.getElementById('step-init'),
        form_fill: document.getElementById('step-fill'),
        form_submit: document.getElementById('step-fill'),
        imap_fetch: document.getElementById('step-otp'),
        otp_received: document.getElementById('step-otp'),
        otp_submitted: document.getElementById('step-verify'),
        feed_scroll: document.getElementById('step-verify'),
        completed: document.getElementById('step-done'),
    };

    if (nodes[step]) {
        Object.values(nodes).forEach(n => {
            if (n && n !== nodes[step] && !n.classList.contains('completed')) {
                n.classList.remove('active');
            }
        });
        nodes[step].classList.add('active');
    }

    if (step === 'form_submit') {
        nodes.init.classList.add('completed');
    } else if (step === 'otp_received') {
        nodes.form_fill.classList.add('completed');
    } else if (step === 'otp_submitted') {
        nodes.imap_fetch.classList.add('completed');
    } else if (step === 'completed') {
        Object.values(nodes).forEach(n => n.classList.add('completed'));
    }
}

function resetStepper() {
    ['step-init', 'step-fill', 'step-otp', 'step-verify', 'step-done'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.className = 'step-node';
    });
    document.getElementById('step-init').classList.add('active');
}

function onTaskFinished(event) {
    setGlobalStatus(false, 'System Ready');
    const submitBtn = document.getElementById('btn-start-register');
    const loginBtn = document.getElementById('btn-start-login');
    const batchBtn = document.getElementById('btn-start-batch');

    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            <span>Start Automated Registration</span>
        `;
    }
    if (loginBtn) {
        loginBtn.disabled = false;
        loginBtn.innerHTML = `<span>Login & Verify Session</span>`;
    }
    if (batchBtn) {
        batchBtn.disabled = false;
        batchBtn.innerHTML = `<span>Start Batch Registration</span>`;
    }

    const data = event.data || {};
    const resultBox = document.getElementById('result-box');
    const resultBadge = document.getElementById('result-badge');
    const resultTitle = document.getElementById('result-title');
    const resultDetails = document.getElementById('result-details');
    const otpPill = document.getElementById('result-otp-pill');
    const otpVal = document.getElementById('result-otp-val');

    resultBox.style.display = 'block';

    if (data.success || event.level === 'success') {
        resultBadge.className = 'badge badge-success';
        resultBadge.innerText = 'Success';
        resultTitle.innerText = 'Account Flow Completed!';
        resultDetails.innerText = data.details || event.message;

        if (data.otp) {
            otpPill.style.display = 'inline-flex';
            otpVal.innerText = data.otp;
        } else {
            otpPill.style.display = 'none';
        }
    } else {
        resultBadge.className = 'badge badge-error';
        resultBadge.innerText = 'Attention';
        resultTitle.innerText = 'Process Terminated';
        resultDetails.innerText = data.details || event.message;
        otpPill.style.display = 'none';
    }
}

function hideResultBox() {
    const box = document.getElementById('result-box');
    if (box) box.style.display = 'none';
}

function addLogEntry(level, title, message, timeStr) {
    const container = document.getElementById('console-logs');
    if (!container) return;

    const row = document.createElement('div');
    row.className = `log-entry ${level}`;

    const t = timeStr || new Date().toTimeString().split(' ')[0];
    row.innerHTML = `
        <span class="log-time">${t}</span>
        <span class="log-tag">${title.toUpperCase()}</span>
        <span class="log-msg">${escapeHtml(message)}</span>
    `;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
}

function setGlobalStatus(running, text) {
    const dot = document.getElementById('global-status-dot');
    const label = document.getElementById('global-status-text');
    if (!dot || !label) return;

    if (running) {
        dot.className = 'status-dot running';
        label.innerText = text || 'Task In Progress';
    } else {
        dot.className = 'status-dot ready';
        label.innerText = text || 'System Ready';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ==========================================
// SMSPool Integration Handlers
// ==========================================
let activeSMSOrderId = null;
let smsPollInterval = null;
let smsTimerInterval = null;
let smsSecondsRemaining = 600;

const btnCheckSMSBalance = document.getElementById('btn-check-smspool-balance');
const btnOrderSMS = document.getElementById('btn-order-sms');
const btnCancelSMS = document.getElementById('btn-cancel-sms');
const smspoolResult = document.getElementById('smspool-result');
const smspoolBalanceText = document.getElementById('smspool-balance-text');

if (btnCheckSMSBalance) {
    btnCheckSMSBalance.addEventListener('click', checkSMSPoolBalance);
}

if (btnOrderSMS) {
    btnOrderSMS.addEventListener('click', orderSMSPoolNumber);
}

if (btnCancelSMS) {
    btnCancelSMS.addEventListener('click', cancelActiveSMSOrder);
}

window.addEventListener('DOMContentLoaded', () => {
    const key = document.getElementById('smspool-api-key')?.value?.trim();
    if (key) {
        checkSMSPoolBalance();
    }
});

async function checkSMSPoolBalance() {
    const key = document.getElementById('smspool-api-key')?.value?.trim();
    if (!key) {
        showResult(smspoolResult, false, 'Please enter your SMSPool API Key.');
        return;
    }

    if (btnCheckSMSBalance) btnCheckSMSBalance.disabled = true;
    if (smspoolBalanceText) smspoolBalanceText.innerText = 'Checking...';

    try {
        const resp = await fetch('/api/smspool/balance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key })
        });
        const data = await resp.json();

        if (data.success) {
            const balStr = `$${Number(data.balance).toFixed(2)}`;
            if (smspoolBalanceText) smspoolBalanceText.innerText = balStr;
            showResult(smspoolResult, true, `Connected to SMSPool! Account Balance: ${balStr} USD`);
        } else {
            if (smspoolBalanceText) smspoolBalanceText.innerText = 'Error';
            showResult(smspoolResult, false, `Balance check failed: ${data.message || 'Invalid API Key'}`);
        }
    } catch (err) {
        if (smspoolBalanceText) smspoolBalanceText.innerText = 'Error';
        showResult(smspoolResult, false, `Network error checking balance: ${err.message}`);
    } finally {
        if (btnCheckSMSBalance) btnCheckSMSBalance.disabled = false;
    }
}

async function orderSMSPoolNumber() {
    const key = document.getElementById('smspool-api-key')?.value?.trim();
    const country = document.getElementById('smspool-country')?.value || 'US';

    if (!key) {
        showResult(smspoolResult, false, 'Please enter your SMSPool API Key first.');
        return;
    }

    if (btnOrderSMS) btnOrderSMS.disabled = true;
    showResult(smspoolResult, true, 'Ordering temporary number for Instagram from SMSPool...');

    try {
        const resp = await fetch('/api/smspool/purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, country, service: '457' })
        });
        const data = await resp.json();

        if (data.success) {
            activeSMSOrderId = data.order_id;
            smsSecondsRemaining = Number(data.expires_in) || 600;

            const activeBox = document.getElementById('smspool-active-box');
            const placeholderBox = document.getElementById('smspool-placeholder-box');
            if (activeBox) activeBox.style.display = 'block';
            if (placeholderBox) placeholderBox.style.display = 'none';

            const phoneDisplay = data.full_number || data.phonenumber;
            document.getElementById('active-order-id').innerText = data.order_id;
            document.getElementById('active-order-phone').innerText = phoneDisplay;
            document.getElementById('active-order-status').innerText = 'Waiting for SMS';
            document.getElementById('active-order-code').innerText = 'Waiting for SMS...';
            document.getElementById('active-order-code').style.color = 'var(--primary)';
            document.getElementById('active-order-raw').innerText = 'Assigned number: ' + phoneDisplay;

            showResult(smspoolResult, true, `Number ${phoneDisplay} acquired! Waiting for verification code...`);

            startSMSCountdown();
            startSMSPolling(key, data.order_id);
            checkSMSPoolBalance();
        } else {
            showResult(smspoolResult, false, `Failed to order number: ${data.message || 'No numbers available'}`);
        }
    } catch (err) {
        showResult(smspoolResult, false, `Error purchasing SMS: ${err.message}`);
    } finally {
        if (btnOrderSMS) btnOrderSMS.disabled = false;
    }
}

function startSMSCountdown() {
    if (smsTimerInterval) clearInterval(smsTimerInterval);
    const timerElem = document.getElementById('active-order-timer');

    smsTimerInterval = setInterval(() => {
        smsSecondsRemaining--;
        if (timerElem) timerElem.innerText = `${smsSecondsRemaining}s`;

        if (smsSecondsRemaining <= 0) {
            clearInterval(smsTimerInterval);
            if (smsPollInterval) clearInterval(smsPollInterval);
            const statusElem = document.getElementById('active-order-status');
            const codeElem = document.getElementById('active-order-code');
            if (statusElem) statusElem.innerText = 'Expired / Refunded';
            if (codeElem) {
                codeElem.innerText = 'Expired';
                codeElem.style.color = '#ef4444';
            }
            checkSMSPoolBalance();
        }
    }, 1000);
}

function startSMSPolling(key, orderId) {
    if (smsPollInterval) clearInterval(smsPollInterval);

    smsPollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/smspool/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, order_id: orderId })
            });
            const data = await resp.json();

            if (data.status === 3 && data.sms) {
                clearInterval(smsPollInterval);
                clearInterval(smsTimerInterval);

                const statusElem = document.getElementById('active-order-status');
                const codeElem = document.getElementById('active-order-code');
                const rawElem = document.getElementById('active-order-raw');

                if (statusElem) {
                    statusElem.innerText = 'Completed';
                    statusElem.style.background = '#ecfdf5';
                    statusElem.style.color = '#059669';
                }

                if (codeElem) {
                    codeElem.innerText = data.sms;
                    codeElem.style.color = '#059669';
                }

                if (rawElem) {
                    rawElem.innerText = data.full_sms || 'Code received successfully!';
                }

                showResult(smspoolResult, true, `Verification code received: ${data.sms}`);
                addLog('smspool', 'SMS Code Received', `Code ${data.sms} for phone verification`, 'success');
            } else if (data.status === 2 || data.status === 5 || data.status === 6) {
                clearInterval(smsPollInterval);
                clearInterval(smsTimerInterval);
                const statusElem = document.getElementById('active-order-status');
                const codeElem = document.getElementById('active-order-code');
                if (statusElem) statusElem.innerText = data.status_text || 'Cancelled';
                if (codeElem) codeElem.innerText = 'Refunded';
                checkSMSPoolBalance();
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 3500);
}

async function cancelActiveSMSOrder() {
    if (!activeSMSOrderId) return;
    const key = document.getElementById('smspool-api-key')?.value?.trim();

    if (btnCancelSMS) btnCancelSMS.disabled = true;

    try {
        const resp = await fetch('/api/smspool/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, order_id: activeSMSOrderId })
        });
        const data = await resp.json();

        if (data.success) {
            if (smsPollInterval) clearInterval(smsPollInterval);
            if (smsTimerInterval) clearInterval(smsTimerInterval);

            const statusElem = document.getElementById('active-order-status');
            const codeElem = document.getElementById('active-order-code');
            if (statusElem) statusElem.innerText = 'Cancelled & Refunded';
            if (codeElem) {
                codeElem.innerText = 'Order Cancelled';
                codeElem.style.color = '#ef4444';
            }

            showResult(smspoolResult, true, 'Order cancelled successfully. Balance refunded!');
            checkSMSPoolBalance();
        } else {
            showResult(smspoolResult, false, `Cancel failed: ${data.message}`);
        }
    } catch (err) {
        showResult(smspoolResult, false, `Error cancelling order: ${err.message}`);
    } finally {
        if (btnCancelSMS) btnCancelSMS.disabled = false;
    }
}
