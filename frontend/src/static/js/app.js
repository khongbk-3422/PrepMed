// app.js

import { getSessions, processSession, reviewSession } from "./api.js";
import {
    pauseOrStopRecording,
    resetRecording,
    setupSpeechRecognition,
    startRecording,
} from "./speech.js";

const el = {
    user: document.getElementById("userSelect"),
    patient: document.getElementById("patientSelect"),
    model: document.getElementById("modelSelect"),
    template: document.getElementById("templateSelect"),

    statusInput: document.getElementById("consultationStatus"),
    statusRadios: document.querySelectorAll("input[name='consultationStatus']"),
    markConfirmed: document.getElementById("markConfirmed"),

    transcript: document.getElementById("transcriptText"),
    structuredData: document.getElementById("structuredData"),
    structuredFields: document.getElementById("structuredFields"),
    description: document.getElementById("extractedDescription"),
    medicine: document.getElementById("extractedMedicine"),
    resultTranscript: document.getElementById("resultTranscript"),
    currentId: document.getElementById("currentConsultationId"),

    startBtn: document.getElementById("startBtn"),
    pauseStopBtn: document.getElementById("pauseStopBtn"),
    resetBtn: document.getElementById("resetBtn"),
    processBtn: document.getElementById("processBtn"),
    saveBtn: document.getElementById("saveReviewBtn"),

    sessionsList: document.getElementById("sessionsList"),
};

let isProcessing = false;
let hasProcessed = false;
let showAllHistory = false;

const HISTORY_LIMIT = 5;

/* Buttons */

function setRecordingButtons(state) {
    const isBusy = state === "processing";
    const isDone = state === "processed";

    el.startBtn.disabled = isBusy || isDone;
    el.pauseStopBtn.disabled = isBusy || isDone;
    el.resetBtn.disabled = isBusy;
    el.processBtn.disabled = isBusy || isDone;

    if (isBusy) {
        el.processBtn.textContent = "Processing...";
    } else if (isDone) {
        el.processBtn.textContent = "Processed";
    } else {
        el.processBtn.textContent = "Process";
    }
}

function resetProcessState() {
    isProcessing = false;
    hasProcessed = false;
    setRecordingButtons("ready");
}

/* Helpers */

function cleanFieldName(name) {
    return String(name).replace(/:$/, "").trim();
}

function formatLabel(name) {
    return cleanFieldName(name)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function normalizeStatus(status) {
    return status === "Confirmed" ? "Confirmed" : "Pending Review";
}

function getStatusLabel(status) {
    return normalizeStatus(status) === "Confirmed" ? "Completed" : "Pending Review";
}

function getStatusClass(status) {
    return normalizeStatus(status) === "Confirmed"
        ? "status-confirmed"
        : "status-pending";
}

function getSelectedStatus() {
    return document.querySelector("input[name='consultationStatus']:checked")?.value
        || "Pending Review";
}

function setStatus(status) {
    const cleanStatus = normalizeStatus(status);

    el.statusInput.value = cleanStatus;

    el.statusRadios.forEach((radio) => {
        radio.checked = radio.value === cleanStatus;
    });

    el.markConfirmed.checked = cleanStatus === "Confirmed";
}

function formatSessionDateTime(createdAt) {
    if (!createdAt) {
        return { date: "No date", time: "" };
    }

    let value = String(createdAt);

    if (!/[zZ]|[+-]\d{2}:\d{2}$/.test(value)) {
        value = `${value}Z`;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return {
            date: String(createdAt).slice(0, 10),
            time: "",
        };
    }

    return {
        date: date.toLocaleDateString("en-CA", {
            timeZone: "Asia/Kuala_Lumpur",
        }),
        time: date.toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
            timeZone: "Asia/Kuala_Lumpur",
        }),
    };
}

function showError(error) {
    console.error(error);
    alert(error.message || "Something went wrong.");
}

/* Clinical fields */

function renderStructuredFields(data) {
    el.structuredFields.innerHTML = "";

    Object.entries(data).forEach(([key, value]) => {
        const cleanKey = cleanFieldName(key);

        const group = document.createElement("div");
        group.className = "clinical-field";

        const label = document.createElement("label");
        label.textContent = `${formatLabel(cleanKey)}:`;

        const textarea = document.createElement("textarea");
        textarea.rows = 2;
        textarea.dataset.fieldKey = cleanKey;
        textarea.value = value || "-";

        group.append(label, textarea);
        el.structuredFields.appendChild(group);
    });

    syncStructuredData();
}

function syncStructuredData() {
    const data = {};

    el.structuredFields.querySelectorAll("[data-field-key]").forEach((field) => {
        data[field.dataset.fieldKey] = field.value.trim() || "-";
    });

    el.structuredData.value = JSON.stringify(data);
}

/* Template */

function getSelectedTemplate() {
    const option = el.template.options[el.template.selectedIndex];

    if (!option) {
        return {
            requiredItems: [],
            defaultDescription: "-",
            defaultMedicine: "-",
        };
    }

    let requiredItems = [];

    try {
        requiredItems = JSON.parse(option.dataset.requiredItems || "[]");
    } catch {
        requiredItems = [];
    }

    return {
        requiredItems,
        defaultDescription: option.dataset.defaultDescription || "-",
        defaultMedicine: option.dataset.defaultMedicine || "-",
    };
}

function updateNoteFromTemplate() {
    const template = getSelectedTemplate();
    const fields = {};

    template.requiredItems.forEach((item) => {
        fields[cleanFieldName(item)] = "-";
    });

    renderStructuredFields(fields);

    el.description.value = template.defaultDescription;
    el.medicine.value = template.defaultMedicine;
    el.currentId.value = "";
    el.resultTranscript.value = "";

    setStatus("Pending Review");
}

/* Session + history */

function showSession(session) {
    el.currentId.value = session.id || "";
    el.transcript.value = session.raw_transcript || "";
    el.resultTranscript.value = session.raw_transcript || "";

    renderStructuredFields(session.extracted_structured_data || {});

    el.description.value = session.extracted_description || "-";
    el.medicine.value = session.extracted_medicine || "-";

    setStatus(session.status || "Pending Review");

    hasProcessed = true;
    setRecordingButtons("processed");
}

function createHistoryItem(session) {
    const item = document.createElement("div");
    const dateTime = formatSessionDateTime(session.created_at);

    item.className = "history-item";

    item.innerHTML = `
        <div class="history-date-row">
            <span class="history-date">${dateTime.date}</span>
            <span class="history-time">${dateTime.time}</span>
        </div>

        <span class="status-badge ${getStatusClass(session.status)}">
            ${getStatusLabel(session.status)}
        </span>

        <button type="button" class="btn btn-light history-open-btn">
            Open
        </button>
    `;

    item.querySelector("button").addEventListener("click", () => {
        showSession(session);
    });

    return item;
}

function createLoadMoreButton(totalSessions) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = "btn history-load-more";
    button.textContent = showAllHistory
        ? "Show Less"
        : `Load More (${totalSessions - HISTORY_LIMIT})`;

    button.addEventListener("click", () => {
        showAllHistory = !showAllHistory;
        refreshHistory();
    });

    return button;
}

async function refreshHistory() {
    const sessions = await getSessions();

    el.sessionsList.innerHTML = "";

    if (!sessions.length) {
        el.sessionsList.innerHTML = `<p class="muted-text">No consultation history yet.</p>`;
        return;
    }

    const visibleSessions = showAllHistory
        ? sessions
        : sessions.slice(0, HISTORY_LIMIT);

    visibleSessions.forEach((session) => {
        el.sessionsList.appendChild(createHistoryItem(session));
    });

    if (sessions.length > HISTORY_LIMIT) {
        el.sessionsList.appendChild(createLoadMoreButton(sessions.length));
    }
}

/* Backend actions */

async function autoSaveAsPendingReview(session) {
    if (!session.id) return;

    await reviewSession(session.id, {
        user_id: Number(el.user.value),
        extracted_structured_data: session.extracted_structured_data || {},
        extracted_description: session.extracted_description || "-",
        extracted_medicine: session.extracted_medicine || "-",
        status: "Pending Review",
        mark_confirmed: false,
    });
}

async function processTranscript() {
    if (isProcessing || hasProcessed) return;

    const transcript = el.transcript.value.trim();

    if (!el.user.value) return alert("Please select a user.");
    if (!el.template.value) return alert("Please select a template.");
    if (!el.model.value) return alert("Please select a model.");
    if (!transcript) return alert("Transcript is empty.");

    const data = {
        patient_id: el.patient.value,
        user_id: el.user.value,
        template_id: el.template.value,
        model_name: el.model.value,
        transcript,
    };

    isProcessing = true;
    setRecordingButtons("processing");

    try {
        const session = await processSession(data);

        session.status = "Pending Review";

        showSession(session);
        await autoSaveAsPendingReview(session);
        await refreshHistory();

        hasProcessed = true;
        setRecordingButtons("processed");
    } catch (error) {
        showError(error);
        resetProcessState();
    } finally {
        isProcessing = false;
    }
}

async function saveReview() {
    if (!el.currentId.value) {
        alert("No consultation selected.");
        return;
    }

    syncStructuredData();

    const status = getSelectedStatus();

    const data = {
        user_id: Number(el.user.value),
        extracted_structured_data: JSON.parse(el.structuredData.value || "{}"),
        extracted_description: el.description.value.trim() || "-",
        extracted_medicine: el.medicine.value.trim() || "-",
        status,
        mark_confirmed: status === "Confirmed",
    };

    try {
        const result = await reviewSession(el.currentId.value, data);

        setStatus(result.current_state || status);
        await refreshHistory();

        alert("Note saved.");
    } catch (error) {
        showError(error);
    }
}

/* Events */

function setupEvents() {
    el.template.addEventListener("change", () => {
        updateNoteFromTemplate();
        resetProcessState();
    });

    el.statusRadios.forEach((radio) => {
        radio.addEventListener("change", () => setStatus(getSelectedStatus()));
    });

    el.startBtn.addEventListener("click", startRecording);
    el.pauseStopBtn.addEventListener("click", pauseOrStopRecording);

    el.resetBtn.addEventListener("click", () => {
        resetRecording();
        updateNoteFromTemplate();
        resetProcessState();
    });

    el.processBtn.addEventListener("click", processTranscript);
    el.saveBtn.addEventListener("click", saveReview);
}

/* Start */

function startApp() {
    setupSpeechRecognition(el.transcript);
    setupEvents();
    updateNoteFromTemplate();
    resetProcessState();
    refreshHistory();
}

document.addEventListener("DOMContentLoaded", startApp);