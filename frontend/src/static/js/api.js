// api.js
// Small helper file for all backend calls.

async function request(path, options = {}) {
    const response = await fetch(path, options);

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = errorData?.detail || "Request failed";
        throw new Error(message);
    }

    return response.json();
}

//all get requests
export function getSessions() {
    return request("/api/sessions");
}

export function getUsers() {
    return request("/api/users");
}

export function getTemplates() {
    return request("/api/templates");
}

export function getModels() {
    return request("/models");
}

//all post requests
export function createUser(data) {
    return request("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}

export function createTemplate(data) {
    return request("/api/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}

export function processSession(data) {
    return request("/api/sessions/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}

export function reviewSession(sessionId, data) {
    return request(`/api/sessions/${sessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
}