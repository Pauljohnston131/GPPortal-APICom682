// Set API base URL (local for dev)
const API_BASE = "http://127.0.0.1:8000";

// Reusable API helpers
async function apiGet(path) {
    const r = await fetch(`${API_BASE}${path}`);
    return r.json();
}

async function apiPost(path, body) {
    const r = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        body
    });
    return r.json();
}

async function apiPut(path, json) {
    const r = await fetch(`${API_BASE}${path}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json)
    });
    return r.json();
}

async function apiDelete(path) {
    const r = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
    return r.json();
}
