// Use local API while developing
const API = "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

// ------------------ UPLOAD (Patient Portal) --------------------
$("form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const pid = $("patientId").value.trim();
    const file = $("file").files[0];

    if (!pid || !file) {
        $("msg").textContent = "Patient ID and file are required.";
        return;
    }

    $("msg").textContent = "Uploading...";

    const fd = new FormData();
    fd.append("patientId", pid);
    fd.append("file", file);

    try {
        const r = await fetch(`${API}/upload`, {
            method: "POST",
            body: fd
        });
        const j = await r.json();

        if (r.ok) {
            $("msg").textContent = "Upload successful.";
            loadPatientRecords();
        } else {
            $("msg").textContent = "Upload failed: " + (j.error || r.status);
        }
    } catch (e) {
        $("msg").textContent = "Error: " + e.message;
    }
});

// ------------------ PATIENT RECORDS LIST --------------------

$("refresh").addEventListener("click", loadPatientRecords);

async function loadPatientRecords() {
    const pid = $("patientId").value.trim();
    if (!pid) {
        $("msg").textContent = "Enter Patient ID first.";
        return;
    }

    $("msg").textContent = "Loading records...";

    try {
        const r = await fetch(`${API}/records?patientId=${encodeURIComponent(pid)}`);
        const j = await r.json();

        const container = $("patient-records");
        container.innerHTML = "";

        if (!r.ok) {
            $("msg").textContent = "Failed to fetch records.";
            return;
        }

        if (!j.records.length) {
            container.innerHTML = `<p class="text-muted">No records found.</p>`;
            $("msg").textContent = "No records found for this patient.";
            return;
        }

        j.records.forEach(rec => {
            const col = document.createElement("div");
            col.className = "col-12";

            const dt = rec.createdAt ? new Date(rec.createdAt * 1000).toLocaleString() : "N/A";
            const notes = rec.gpNotes || "(no notes)";

            col.innerHTML = `
                <div class="p-3 bg-white border rounded">
                    <div class="d-flex">
                        <div class="me-3">
                            <a href="${rec.blobUrl}" target="_blank">
                                <img src="${rec.blobUrl}" class="preview-img" onerror="this.style.display='none'"/>
                            </a>
                        </div>
                        <div>
                            <div><strong>Status:</strong> ${rec.status}</div>
                            <div><strong>Uploaded:</strong> ${dt}</div>
                            <div class="small text-muted"><strong>GP Notes:</strong> ${notes}</div>
                            <div class="small text-muted mt-1">Record ID: ${rec.id}</div>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(col);
        });

        $("msg").textContent = `Loaded ${j.records.length} records.`;
    } catch (err) {
        $("msg").textContent = "Error loading records: " + err.message;
    }
}

// ------------------ GP DASHBOARD LIST --------------------

$("gpLoad").addEventListener("click", loadGpRecords);

async function loadGpRecords() {
    const pid = $("gpPatientId").value.trim();
    const container = $("gp-records");
    container.innerHTML = "";

    if (!pid) {
        container.innerHTML = `<p class="text-muted">Enter a Patient ID to load their records.</p>`;
        return;
    }

    try {
        const r = await fetch(`${API}/records?patientId=${encodeURIComponent(pid)}`);
        const j = await r.json();

        if (!r.ok) {
            container.innerHTML = `<p class="text-danger">Failed to load records.</p>`;
            return;
        }

        if (!j.records.length) {
            container.innerHTML = `<p class="text-muted">No records found for this patient.</p>`;
            return;
        }

        j.records.forEach(rec => {
            const col = document.createElement("div");
            col.className = "col-12";

            const dt = rec.createdAt ? new Date(rec.createdAt * 1000).toLocaleString() : "N/A";

            col.innerHTML = `
                <div class="p-3 bg-white border rounded">
                    <div class="d-flex">
                        <div class="me-3">
                            <a href="${rec.blobUrl}" target="_blank">
                                <img src="${rec.blobUrl}" class="preview-img" onerror="this.style.display='none'"/>
                            </a>
                        </div>
                        <div class="flex-grow-1">
                            <div><strong>Status:</strong> <span id="status-${rec.id}">${rec.status}</span></div>
                            <div><strong>Uploaded:</strong> ${dt}</div>
                            <div class="small text-muted mb-2">
                                <strong>Record ID:</strong> ${rec.id}
                            </div>
                            <div class="mb-2">
                                <label class="form-label small mb-1">Update Status</label>
                                <input type="text" class="form-control form-control-sm" id="input-status-${rec.id}" placeholder="e.g. reviewed">
                            </div>
                            <div class="mb-2">
                                <label class="form-label small mb-1">GP Notes</label>
                                <textarea class="form-control form-control-sm" id="input-notes-${rec.id}" rows="2" placeholder="Add clinical notes">${rec.gpNotes || ""}</textarea>
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="saveReview('${rec.id}')">
                                Save Review
                            </button>
                            <span class="small text-muted ms-2" id="msg-${rec.id}"></span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(col);
        });

    } catch (err) {
        container.innerHTML = `<p class="text-danger">Error loading records: ${err.message}</p>`;
    }
}

// ------------------ GP REVIEW SAVE --------------------

async function saveReview(recordId) {
    const statusInput = document.getElementById(`input-status-${recordId}`);
    const notesInput = document.getElementById(`input-notes-${recordId}`);
    const msgSpan = document.getElementById(`msg-${recordId}`);

    const payload = {};
    if (statusInput.value.trim()) {
        payload.status = statusInput.value.trim();
    }
    payload.gpNotes = notesInput.value.trim();

    msgSpan.textContent = "Saving...";

    try {
        const r = await fetch(`${API}/record/${encodeURIComponent(recordId)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const j = await r.json();

        if (!r.ok) {
            msgSpan.textContent = "Error: " + (j.error || r.status);
        } else {
            msgSpan.textContent = "Saved.";
            if (j.status) {
                document.getElementById(`status-${recordId}`).textContent = j.status;
            }
        }
    } catch (err) {
        msgSpan.textContent = "Error: " + err.message;
    }
}
