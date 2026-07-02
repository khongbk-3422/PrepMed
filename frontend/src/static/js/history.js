// history.js
// Optional page for showing all consultation history.

import { getSessions } from "./api.js";

const sessionsList = document.getElementById("sessionsList");

function makeSessionCard(session) {
    const card = document.createElement("div");
    card.className = "history-item";

    card.innerHTML = `
        <div class="history-date">
            ${session.created_at ? session.created_at.slice(0, 10) : "No date"}
        </div>

        <p>Status: ${session.status || "Draft"}</p>
        <p>Patient ID: ${session.patient_id || "-"}</p>
        <p>${session.raw_transcript || "No transcript"}</p>
    `;

    return card;
}

async function loadHistory() {
    try {
        const sessions = await getSessions();

        sessionsList.innerHTML = "";

        if (!sessions.length) {
            sessionsList.innerHTML = `<p class="muted-text">No consultation history yet.</p>`;
            return;
        }

        sessions.forEach((session) => {
            sessionsList.appendChild(makeSessionCard(session));
        });
    } catch (error) {
        sessionsList.textContent = error.message;
    }
}

document.addEventListener("DOMContentLoaded", loadHistory);