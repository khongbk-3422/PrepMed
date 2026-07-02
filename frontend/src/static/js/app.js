// app.js
import { getSessions, processSession, reviewSession } from "./api.js";
import { pauseOrStopRecording, resetRecording, setupSpeechRecognition, startRecording} from "./speech.js";

// HTML elements
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

// Small helpers
function cleanFieldName(name) {
    return String(name).replace(/:$/, "").trim();
}

function formatLabel(name) {
    return cleanFieldName(name)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getSelectedStatus() {
    return document.querySelector("input[name='consultationStatus']:checked")?.value || "Draft";
}

function setStatus(status) {
    el.statusInput.value = status;

    el.statusRadios.forEach((radio) => {
        radio.checked = radio.value === status;
    });

    el.markConfirmed.checked = status === "Confirmed";
}

function getStatusClass(status) {
    if (status === "Confirmed") return "status-confirmed";
    if (status === "Pending Review") return "status-pending";
    return "status-draft";
}

function showError(error) {
    console.error(error);
    alert(error.message || "Something went wrong.");
}

// Structured clinical fields
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

// Template handling
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
    setStatus("Draft");
}

// Session display + history
function showSession(session) {
    el.currentId.value = session.id || "";
    el.transcript.value = session.raw_transcript || "";
    el.resultTranscript.value = session.raw_transcript || "";

    renderStructuredFields(session.extracted_structured_data || {});

    el.description.value = session.extracted_description || "-";
    el.medicine.value = session.extracted_medicine || "-";

    setStatus(session.status || "Draft");
}

function createHistoryItem(session) {
    const item = document.createElement("div");
    item.className = "history-item";

    item.innerHTML = `
        <div class="history-date">
            ${session.created_at ? session.created_at.slice(0, 10) : "No date"}
        </div>

        <span class="status-badge ${getStatusClass(session.status)}">
            ${session.status || "Draft"}
        </span>

        <button type="button" class="btn btn-light history-open-btn">
            Open
        </button>
    `;

    item.querySelector("button").addEventListener("click", () => showSession(session));

    return item;
}

async function refreshHistory() {
    const sessions = await getSessions();

    el.sessionsList.innerHTML = "";

    if (!sessions.length) {
        el.sessionsList.innerHTML = `<p class="muted-text">No consultation history yet.</p>`;
        return;
    }

    sessions.forEach((session) => {
        el.sessionsList.appendChild(createHistoryItem(session));
    });
}

// Backend actions
async function processTranscript() {
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

    el.processBtn.disabled = true;

    try {
        const session = await processSession(data);
        showSession(session);
        await refreshHistory();
    } catch (error) {
        showError(error);
    } finally {
        el.processBtn.disabled = false;
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

// Events
function setupEvents() {
    el.template.addEventListener("change", updateNoteFromTemplate);

    el.statusRadios.forEach((radio) => {
        radio.addEventListener("change", () => setStatus(getSelectedStatus()));
    });

    el.startBtn.addEventListener("click", startRecording);
    el.pauseStopBtn.addEventListener("click", pauseOrStopRecording);

    el.resetBtn.addEventListener("click", () => {
        resetRecording();
        updateNoteFromTemplate();
    });

    el.processBtn.addEventListener("click", processTranscript);
    el.saveBtn.addEventListener("click", saveReview);
}

// Start app
function startApp() {
    setupSpeechRecognition(el.transcript);
    setupEvents();
    updateNoteFromTemplate();
    refreshHistory();
}

document.addEventListener("DOMContentLoaded", startApp);