const $ = (id) => document.getElementById(id);

const API_URL = "/api/checkout";
const params = new URLSearchParams(window.location.search);
const chargeId = params.get("id");
let countdownInterval = null;
let pollInterval = null;
let isPixRendered = false;

// Strict validation on load: only allows pure digits (0-9)
if (!chargeId || !/^\d+$/.test(chargeId)) {
    window.location.href = "checkout";
    throw new Error("ID inválido. Redirecionando...");
}

async function fetchStatus() {
    try {
        const res = await fetch(`${API_URL}/${chargeId}`);

        // Handle invalid ID or charge not found
        if (res.status === 404 || res.status === 422) {
            window.location.href = "checkout";
            return null;
        }

        if (!res.ok) throw new Error("Erro na rede");

        const data = await res.json();
        return data;
    } catch (e) {
        console.error("Erro ao buscar status:", e);
        return null;
    }
}

async function startPolling() {
    if (!chargeId || !/^\d+$/.test(chargeId)) return;

    // Initial check
    const initialData = await fetchStatus();
    if (!initialData) return;

    handleState(initialData);

    // Continuous polling every 5 seconds
    pollInterval = setInterval(async () => {
        const data = await fetchStatus();
        if (data) {
            handleState(data);
        }
    }, 5000);
}

function handleState(data) {
    // Update customer name once
    if (data.customer_name) {
        $("customerName").textContent = `Cliente: ${data.customer_name}`;
    }

    // 1. If completed, stop everything and show success
    if (data.status === "completed") {
        stopAll();
        showSuccessState();
        return;
    }

    // 2. If we have PIX data and haven't rendered yet, render it
    if (data.br_code && !isPixRendered) {
        renderPIX(data);
        isPixRendered = true;
    }
}

function stopAll() {
    if (pollInterval) clearInterval(pollInterval);
    if (countdownInterval) clearInterval(countdownInterval);
}

function renderPIX(data) {
    $("qrLoading").style.display = "none";
    $("qrContent").style.display = "flex";
    $("paymentStatus").innerHTML = '<span class="dot"></span> Aguardando pagamento';

    // Limit title if needed
    $("qrcode").innerHTML = ""; // Clear loader/previous
    new QRCode($("qrcode"), {
        text: data.br_code,
        width: 220,
        height: 220,
        correctLevel: QRCode.CorrectLevel.M
    });

    $("pixText").value = data.br_code;

    if (data.expires_at) {
        startCountdown(data.expires_at);
    }
}

function startCountdown(expiresAt) {
    const target = new Date(expiresAt).getTime();

    countdownInterval = setInterval(() => {
        const now = new Date().getTime();
        const diff = target - now;

        if (diff <= 0) {
            clearInterval(countdownInterval);
            $("expires").innerHTML = "PIX Expirado. Gere um novo.";
            $("expires").style.color = "var(--danger)";
            $("paymentStatus").innerHTML = '<span class="dot" style="background:var(--danger)"></span> Expirado';
            return;
        }

        const minutes = Math.floor(diff / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        $("expires").innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            Expira em: ${minutes}:${seconds < 10 ? '0' : ''}${seconds}
        `;
    }, 1000);
}

function showSuccessState() {
    // UI changes for success
    $("qrLoading").style.display = "none";
    $("qrArea").innerHTML = `
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 64px; margin-bottom: 20px;">✅</div>
            <h2 style="color: #4caf50; margin-bottom: 10px;">Pagamento Confirmado!</h2>
            <p style="color: var(--text-muted); line-height: 1.5;">Obrigado! Seu pagamento foi processado com sucesso. Você receberá as próximas instruções via WhatsApp em instantes.</p>
        </div>
    `;
}

$("copyBtn").onclick = async () => {
    const text = $("pixText").value;
    try {
        await navigator.clipboard.writeText(text);
        showCopyFeedback();
    } catch {
        $("pixText").select();
        document.execCommand("copy");
        showCopyFeedback();
    }
};

function showCopyFeedback() {
    const originalText = $("copyBtn").textContent;
    $("copyBtn").textContent = "Copiado! ✅";
    $("copyBtn").classList.add("btn-success");
    setTimeout(() => {
        $("copyBtn").textContent = originalText;
        $("copyBtn").classList.remove("btn-success");
    }, 2000);
}

document.addEventListener("DOMContentLoaded", startPolling);
