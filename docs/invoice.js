// Invoices: Jarvis fills in a draft, someone checks and edits it on screen, then prints, saves a PDF or emails it.
// Totals are always worked out here, never by Claude. Drafts live in memory only; your business details are saved.
const $ = (id) => document.getElementById(id);

const BUSINESS_KEY = "jarvis.business";
const DEFAULT_BUSINESS = { name: "", address: "", phone: "", email: "", payment: "", currency: "USD", nextNumber: 1001 };

export function loadBusiness() {
  try { return { ...DEFAULT_BUSINESS, ...JSON.parse(localStorage.getItem(BUSINESS_KEY) || "{}") }; }
  catch { return { ...DEFAULT_BUSINESS }; }
}
function saveBusiness(b) {
  try { localStorage.setItem(BUSINESS_KEY, JSON.stringify(b)); return true; } catch { return false; }
}

// "$1,200.50", "1200.5" or 1200.5 become 120050 cents; anything else is null.
export function parseMoney(value) {
  if (typeof value === "number") return Number.isFinite(value) ? Math.round(value * 100) : null;
  const text = String(value ?? "").replace(/[$,\s]/g, "");
  if (!text) return 0;
  if (!/^-?\d*\.?\d{0,2}$/.test(text) || text === "." || text === "-") return null;
  return Math.round(parseFloat(text) * 100);
}
function money(cents, currency) {
  try { return new Intl.NumberFormat("en-US", { style: "currency", currency: currency || "USD" }).format(cents / 100); }
  catch { return (cents / 100).toFixed(2) + " " + (currency || ""); }
}

// VINs are 17 characters, never use I, O or Q, and North American ones carry a check digit in position 9.
const VIN_VALUES = { A: 1, B: 2, C: 3, D: 4, E: 5, F: 6, G: 7, H: 8, J: 1, K: 2, L: 3, M: 4, N: 5, P: 7, R: 9, S: 2, T: 3, U: 4, V: 5, W: 6, X: 7, Y: 8, Z: 9 };
const VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2];
export function vinWarning(raw) {
  const vin = String(raw || "").toUpperCase().replace(/\s+/g, "");
  if (!vin) return "";
  if (/[IOQ]/.test(vin)) return "VINs never contain the letters I, O or Q. Check for a 1 or 0 typed as a letter.";
  if (!/^[A-Z0-9]+$/.test(vin)) return "A VIN has only letters and numbers.";
  if (vin.length !== 17) return `A VIN has 17 characters; this one has ${vin.length}.`;
  let sum = 0;
  for (let i = 0; i < 17; i++) sum += (/\d/.test(vin[i]) ? Number(vin[i]) : VIN_VALUES[vin[i]]) * VIN_WEIGHTS[i];
  const check = sum % 11 === 10 ? "X" : String(sum % 11);
  return vin[8] === check ? "" : "The VIN's check digit doesn't match, so a character may be wrong. (Some imported cars' VINs don't use a check digit.)";
}

const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const isDate = (s) => /^\d{4}-\d{2}-\d{2}$/.test(String(s || ""));

// A draft from Claude's tool input or from scratch. Amounts stay as text so the checker sees exactly what was given.
export function makeDraft(input = {}) {
  const items = (Array.isArray(input.items) ? input.items : [])
    .map((it) => ({ description: String(it?.description ?? "").trim(), amount: it?.amount == null ? "" : String(it.amount) }))
    .filter((it) => it.description || it.amount);
  return {
    number: String(loadBusiness().nextNumber),
    date: today(),
    due: isDate(input.due_date) ? input.due_date : "",
    name: String(input.customer_name ?? "").trim(),
    email: String(input.customer_email ?? "").trim(),
    phone: String(input.customer_phone ?? "").trim(),
    address: String(input.customer_address ?? "").trim(),
    vehicle: String(input.vehicle ?? "").trim(),
    vin: String(input.vin ?? "").toUpperCase().replace(/\s+/g, ""),
    items: items.length ? items : [{ description: "", amount: "" }],
    paid: input.amount_paid == null ? "" : String(input.amount_paid),
    notes: String(input.notes ?? "").trim(),
  };
}

export function totals(draft) {
  const amounts = draft.items.map((it) => parseMoney(it.amount));
  const paid = parseMoney(draft.paid);
  const bad = amounts.some((a) => a === null) || paid === null;
  const subtotal = amounts.reduce((s, a) => s + (a || 0), 0);
  return { subtotal, paid: paid || 0, balance: subtotal - (paid || 0), bad };
}

// ---------- the editor ----------
let draft = null;

const FIELDS = { invNumber: "number", invDate: "date", invDue: "due", invName: "name", invEmail: "email", invPhone: "phone",
  invAddress: "address", invVehicle: "vehicle", invVin: "vin", invPaid: "paid", invNotes: "notes" };

// Works on the draft itself, so closing and reopening it from its card keeps the office's edits.
export function openInvoice(d = makeDraft()) {
  draft = d;
  for (const [id, key] of Object.entries(FIELDS)) $(id).value = draft[key];
  renderItems();
  update();
  $("invoice").hidden = false;
  $("invName").focus({ preventScroll: true });
  $("invoice").scrollTop = 0;
}

function renderItems() {
  const list = $("invItems");
  list.replaceChildren();
  draft.items.forEach((it, i) => {
    const row = document.createElement("div");
    row.className = "inv-item";
    const desc = Object.assign(document.createElement("input"), { type: "text", value: it.description, placeholder: "Description (e.g. Transport, Doc fee)" });
    desc.setAttribute("aria-label", `Line ${i + 1} description`);
    desc.oninput = () => { it.description = desc.value; update(); };
    const amt = Object.assign(document.createElement("input"), { type: "text", value: it.amount, placeholder: "0.00", inputMode: "decimal" });
    amt.setAttribute("aria-label", `Line ${i + 1} amount`);
    amt.className = "inv-amount";
    amt.oninput = () => { it.amount = amt.value; update(); };
    const del = Object.assign(document.createElement("button"), { type: "button", className: "toggle", textContent: "Remove" });
    del.onclick = () => { draft.items.splice(i, 1); if (!draft.items.length) draft.items.push({ description: "", amount: "" }); renderItems(); update(); };
    row.append(desc, amt, del);
    list.appendChild(row);
  });
}

function problems() {
  const out = [];
  const t = totals(draft);
  if (!draft.name) out.push("Add the customer's name.");
  if (!draft.items.some((it) => it.description && parseMoney(it.amount))) out.push("Add at least one line with a description and an amount.");
  if (t.bad) out.push("One of the amounts isn't a number. Use digits like 1200 or 1,200.50.");
  const vin = vinWarning(draft.vin);
  if (vin) out.push(vin);
  if (draft.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email)) out.push("The customer's email doesn't look right.");
  if (t.balance < 0) out.push("The amount paid is more than the total.");
  return out;
}

function update() {
  const b = loadBusiness();
  const t = totals(draft);
  $("invSubtotal").textContent = money(t.subtotal, b.currency);
  $("invPaidOut").textContent = money(t.paid, b.currency);
  $("invBalance").textContent = money(t.balance, b.currency);
  const list = problems();
  $("invProblems").replaceChildren(...list.map((p) => Object.assign(document.createElement("li"), { textContent: p })));
  $("invProblems").hidden = !list.length;
  $("invEmailBtn").disabled = !draft.email;
}

// Plain text for email and copying.
function invoiceText() {
  const b = loadBusiness();
  const t = totals(draft);
  const lines = [
    `INVOICE #${draft.number}`, b.name, b.address, [b.phone, b.email].filter(Boolean).join(" · "), "",
    `Date: ${draft.date}`, `Due: ${draft.due || "On receipt"}`, "",
    "Bill to:", draft.name, draft.address, [draft.phone, draft.email].filter(Boolean).join(" · "), "",
  ];
  if (draft.vehicle || draft.vin) lines.push(`Vehicle: ${draft.vehicle}${draft.vin ? `  VIN: ${draft.vin}` : ""}`, "");
  for (const it of draft.items) if (it.description || it.amount) lines.push(`${it.description}: ${money(parseMoney(it.amount) || 0, b.currency)}`);
  lines.push("", `Subtotal: ${money(t.subtotal, b.currency)}`);
  if (t.paid) lines.push(`Paid: ${money(t.paid, b.currency)}`);
  lines.push(`Balance due: ${money(t.balance, b.currency)}`);
  if (b.payment) lines.push("", "How to pay:", b.payment);
  if (draft.notes) lines.push("", draft.notes);
  return lines.filter((l, i, all) => !(l === "" && all[i - 1] === "")).join("\n").trim();
}

// The printed page, built with textContent so nothing typed in can become live HTML.
function renderPrint() {
  const b = loadBusiness();
  const t = totals(draft);
  const el = (tag, text, cls) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; };
  const page = $("invPrint");
  page.replaceChildren();
  const head = el("div", null, "p-head");
  const from = el("div");
  from.append(el("h1", b.name || "Invoice"), el("p", b.address), el("p", [b.phone, b.email].filter(Boolean).join(" · ")));
  const meta = el("div", null, "p-meta");
  meta.append(el("h2", `Invoice #${draft.number}`), el("p", `Date: ${draft.date}`), el("p", `Due: ${draft.due || "On receipt"}`));
  head.append(from, meta);
  const to = el("div", null, "p-to");
  to.append(el("h3", "Bill to"), el("p", draft.name), el("p", draft.address), el("p", [draft.phone, draft.email].filter(Boolean).join(" · ")));
  page.append(head, to);
  if (draft.vehicle || draft.vin) page.append(el("p", `Vehicle: ${draft.vehicle}${draft.vin ? ` · VIN ${draft.vin}` : ""}`, "p-vehicle"));
  const table = el("table");
  const hr = el("tr"); hr.append(el("th", "Description"), el("th", "Amount"));
  table.append(hr);
  for (const it of draft.items) {
    if (!it.description && !it.amount) continue;
    const tr = el("tr"); tr.append(el("td", it.description), el("td", money(parseMoney(it.amount) || 0, b.currency)));
    table.append(tr);
  }
  const sums = [["Subtotal", t.subtotal], ...(t.paid ? [["Paid", t.paid]] : []), ["Balance due", t.balance]];
  for (const [label, cents] of sums) {
    const tr = el("tr", null, label === "Balance due" ? "p-total" : "p-sum"); tr.append(el("td", label), el("td", money(cents, b.currency)));
    table.append(tr);
  }
  page.append(table);
  if (b.payment) page.append(el("h3", "How to pay"), el("p", b.payment, "p-pre"));
  if (draft.notes) page.append(el("p", draft.notes, "p-pre"));
}

// Using an invoice number moves the next one along, so two invoices don't share a number.
function useNumber() {
  const b = loadBusiness();
  if (String(b.nextNumber) === String(draft.number)) { b.nextNumber = Number(draft.number) + 1; saveBusiness(b); }
}

export function initInvoices({ say }) {
  for (const [id, key] of Object.entries(FIELDS)) {
    $(id).addEventListener("input", () => { draft[key] = $(id).value; if (key === "vin") draft.vin = draft.vin.toUpperCase(); update(); });
  }
  $("invAddItem").onclick = () => { draft.items.push({ description: "", amount: "" }); renderItems(); update(); };
  $("invClose").onclick = () => { $("invoice").hidden = true; };
  $("invPrintBtn").onclick = () => {
    if (problems().length && !confirm("This invoice still has problems listed in orange. Print anyway?")) return;
    renderPrint(); useNumber(); window.print();
  };
  $("invEmailBtn").onclick = () => {
    if (problems().length && !confirm("This invoice still has problems listed in orange. Email anyway?")) return;
    const b = loadBusiness();
    const subject = `Invoice #${draft.number}${b.name ? " from " + b.name : ""}`;
    useNumber();
    location.href = `mailto:${encodeURIComponent(draft.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(invoiceText())}`;
  };
  $("invCopyBtn").onclick = async () => {
    try { await navigator.clipboard.writeText(invoiceText()); say("Invoice copied. Paste it wherever you need it."); }
    catch { say("I couldn't copy it. Use Print or Email instead."); }
  };

  // Business details in Settings.
  const bizFields = { bizName: "name", bizAddress: "address", bizPhone: "phone", bizEmail: "email", bizPayment: "payment", bizCurrency: "currency", bizNext: "nextNumber" };
  const fill = () => { const b = loadBusiness(); for (const [id, key] of Object.entries(bizFields)) $(id).value = b[key]; };
  fill();
  $("saveBusiness").onclick = () => {
    const b = loadBusiness();
    for (const [id, key] of Object.entries(bizFields)) b[key] = $(id).value.trim();
    b.currency = (b.currency || "USD").toUpperCase();
    const next = parseInt(b.nextNumber, 10);
    b.nextNumber = Number.isFinite(next) && next > 0 ? next : 1001;
    say(saveBusiness(b) ? "Business details saved for invoices." : "I couldn't save the business details in this browser.");
    fill();
  };
}
