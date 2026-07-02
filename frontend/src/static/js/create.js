// create.js
// Handles add user and add template pages.

import { createTemplate, createUser, getUsers } from "./api.js";

const el = {
    userForm: document.getElementById("userForm"),
    templateForm: document.getElementById("templateForm"),
    status: document.getElementById("createStatus"),
    templateUser: document.getElementById("templateUserSelect"),

    username: document.getElementById("username"),
    fullName: document.getElementById("fullName"),
    role: document.getElementById("role"),

    templateTitle: document.getElementById("templateTitle"),
    requiredItems: document.getElementById("requiredItems"),
    defaultDescription: document.getElementById("defaultDescription"),
    defaultMedicine: document.getElementById("defaultMedicine"),
};

function setStatus(message) {
    if (el.status) {
        el.status.textContent = message;
    }
}

function cleanRequiredItems(text) {
    return text
        .split(/[,\n]/)
        .map((item) => item.trim())
        .map((item) => item.replace(/:$/, ""))
        .filter(Boolean);
}

async function loadUsersForTemplate() {
    if (!el.templateUser) return;

    const users = await getUsers();
    el.templateUser.innerHTML = "";

    if (!users.length) {
        el.templateUser.innerHTML = `<option value="">No users found</option>`;
        return;
    }

    users.forEach((user) => {
        const option = document.createElement("option");
        option.value = user.id;
        option.textContent = `${user.full_name} (${user.role})`;

        el.templateUser.appendChild(option);
    });
}

async function handleCreateUser(event) {
    event.preventDefault();

    const data = {
        username: el.username.value.trim(),
        full_name: el.fullName.value.trim(),
        role: el.role.value,
    };

    if (!data.username || !data.full_name) {
        setStatus("Please fill in all fields.");
        return;
    }

    try {
        setStatus("Creating user...");
        await createUser(data);

        el.userForm.reset();
        setStatus("User created successfully.");
    } catch (error) {
        setStatus(error.message);
    }
}

async function handleCreateTemplate(event) {
    event.preventDefault();

    const data = {
        title: el.templateTitle.value.trim(),
        required_items: cleanRequiredItems(el.requiredItems.value),
        default_description: el.defaultDescription.value.trim() || "-",
        default_medicine: el.defaultMedicine.value.trim() || "-",
        user_id: Number(el.templateUser.value),
    };

    if (!data.title || !data.required_items.length || !data.user_id) {
        setStatus("Please fill in all required fields.");
        return;
    }

    try {
        setStatus("Creating template...");
        await createTemplate(data);

        el.templateForm.reset();
        await loadUsersForTemplate();

        setStatus("Template created successfully.");
    } catch (error) {
        setStatus(error.message);
    }
}

async function startCreatePage() {
    if (el.userForm) {
        el.userForm.addEventListener("submit", handleCreateUser);
    }

    if (el.templateForm) {
        el.templateForm.addEventListener("submit", handleCreateTemplate);
        await loadUsersForTemplate();
    }
}

document.addEventListener("DOMContentLoaded", startCreatePage);