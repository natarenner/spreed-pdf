// ====== CONFIG ======
const API_URL = "/api/checkout";

// ====== DOM ======
const $ = (id) => document.getElementById(id);

const form = $("checkoutForm");
const btn = $("nextBtn");
const statusEl = $("status");
const qrArea = $("qrArea");
const pixTextEl = $("pixText");
const expiresEl = $("expires");
const qrcodeEl = $("qrcode");
const copyBtn = $("copyBtn");
const newBtn = $("newBtn");

let iti = null;   // intl-tel-input instance

// ====== Helpers ======
function setStatus(msg) {
  statusEl.textContent = msg || "";
}

function setError(field, msg) {
  const el = $("err-" + field);
  el.textContent = msg || "";
}

function clearErrors() {
  ["name", "email", "whatsapp", "cpf"].forEach((k) => setError(k, ""));
}

function onlyDigits(s) {
  return (s || "").replace(/\D+/g, "");
}

// ====== Email validation ======
function validateEmail(email) {
  const v = (email || "").trim();
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!re.test(v)) return "Informe um email válido.";
  return null;
}

// ====== CPF validation (real) ======
function isRepeatedSequence(d) {
  return /^(\d)\1{10}$/.test(d);
}

function calcCpfDigit(base) {
  let sum = 0;
  for (let i = 0; i < base.length; i++) {
    sum += Number(base[i]) * (base.length + 1 - i);
  }
  const mod = sum % 11;
  return mod < 2 ? 0 : 11 - mod;
}

function isValidCPF(cpfRaw) {
  const d = onlyDigits(cpfRaw);
  if (d.length !== 11) return false;
  if (isRepeatedSequence(d)) return false;

  const n1to9 = d.slice(0, 9);
  const dig1 = calcCpfDigit(n1to9);

  const n1to10 = d.slice(0, 9) + String(dig1);
  const dig2 = calcCpfDigit(n1to10);

  return d === (n1to9 + String(dig1) + String(dig2));
}

// ====== CPF mask ======
function formatCPF(digits) {
  const d = digits.slice(0, 11);
  let out = d;
  if (d.length > 3) out = d.slice(0, 3) + "." + d.slice(3);
  if (d.length > 6) out = out.slice(0, 7) + "." + d.slice(6);
  if (d.length > 9) out = out.slice(0, 11) + "-" + d.slice(9);
  return out;
}

// ====== QR ======
function renderQr(text) {
  qrcodeEl.innerHTML = "";
  new QRCode(qrcodeEl, {
    text,
    width: 220,
    height: 220,
    correctLevel: QRCode.CorrectLevel.M
  });
}

function showPixArea() {
  qrArea.style.display = "block";
}

function resetPixArea() {
  qrcodeEl.innerHTML = "";
  pixTextEl.value = "";
  expiresEl.textContent = "";
  qrArea.style.display = "none";
}

// ====== Phone (intl-tel-input) ======
function initPhone() {
  const input = $("whatsapp");

  iti = window.intlTelInput(input, {
    initialCountry: "br",
    separateDialCode: true,
    nationalMode: true,
    autoPlaceholder: "aggressive",
    formatOnDisplay: true,
    utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@19.5.7/build/js/utils.js"
  });

  input.addEventListener("blur", () => {
    const err = validateWhatsApp();
    setError("whatsapp", err || "");
  });
}

function validateWhatsApp() {
  if (!iti) return "Campo de WhatsApp não inicializado.";

  const inputVal = $("whatsapp").value.trim();
  if (!inputVal) return "Informe seu WhatsApp.";

  if (!iti.isValidNumber()) {
    return "Informe um WhatsApp válido (com DDD).";
  }

  const e164 = iti.getNumber(); // +5511999999999
  const digits = onlyDigits(e164);
  if (digits.length < 10 || digits.length > 15) {
    return "WhatsApp inválido.";
  }

  return null;
}

function getWhatsAppE164() {
  return iti.getNumber();
}

// ====== Backend call ======
async function createPixCharge(payload) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = data?.message || "Falha ao gerar o PIX. Tente novamente.";
    throw new Error(msg);
  }

  return data;
}

// ====== Submit ======
async function onSubmit(e) {
  e.preventDefault();
  clearErrors();
  setStatus("");

  const name = $("name").value.trim();
  const email = $("email").value.trim();
  const cpf = $("cpf").value.trim();

  if (name.length < 2) setError("name", "Informe seu nome.");

  const emailErr = validateEmail(email);
  if (emailErr) setError("email", emailErr);

  const wpErr = validateWhatsApp();
  if (wpErr) setError("whatsapp", wpErr);

  if (!cpf) {
    setError("cpf", "Informe seu CPF.");
  } else if (!isValidCPF(cpf)) {
    setError("cpf", "CPF inválido.");
  }

  const hasErrors =
    $("err-name").textContent ||
    $("err-email").textContent ||
    $("err-whatsapp").textContent ||
    $("err-cpf").textContent;

  if (hasErrors) return;

  btn.disabled = true;
  setStatus("Registrando pedido...");

  try {
    const payload = {
      name,
      email,
      cpf: onlyDigits(cpf),
      whatsapp: getWhatsAppE164(),
    };

    const initialData = await createPixCharge(payload);
    const chargeId = initialData.id;

    setStatus("Redirecionando para o pagamento...");

    // Redirect to the dedicated payment page
    window.location.href = `payment?id=${chargeId}`;

  } catch (err) {
    setStatus(err?.message || "Erro ao iniciar checkout.");
  } finally {
    btn.disabled = false;
  }
}

// ====== Copy / New ======
async function copyPix() {
  const text = pixTextEl.value || "";
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    setStatus("Código PIX copiado ✅");
  } catch {
    pixTextEl.focus();
    pixTextEl.select();
    document.execCommand("copy");
    setStatus("Código PIX copiado ✅");
  }
}

function onNew() {
  resetPixArea();
  setStatus("");
}

// ====== Init ======
document.addEventListener("DOMContentLoaded", () => {
  initPhone();

  $("cpf").addEventListener("input", (ev) => {
    const d = onlyDigits(ev.target.value);
    ev.target.value = formatCPF(d);
  });

  form.addEventListener("submit", onSubmit);
  copyBtn.addEventListener("click", copyPix);
  newBtn.addEventListener("click", onNew);
});
