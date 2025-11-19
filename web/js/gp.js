// -------------------------------
// GP DASHBOARD – WITH IMAGE PREVIEW
// -------------------------------
const gpInput = document.getElementById("gpPatientId");
const gpLoadBtn = document.getElementById("gpLoadBtn");
const gpRecordsList = document.getElementById("gpRecordsList");
const filterStatus = document.getElementById("filterStatus");
const applyFilter = document.getElementById("applyFilter");
const detailContent = document.getElementById("detailContent");
const detailFile = document.getElementById("detailFile");
const detailDate = document.getElementById("detailDate");
const detailStatus = document.getElementById("detailStatus");
const detailNotes = document.getElementById("detailNotes");
const saveDetail = document.getElementById("saveDetail");
const deleteDetail = document.getElementById("deleteDetail");
const detailMsg = document.getElementById("detailMsg");

let currentRecords = [];
let selectedRecord = null;

gpLoadBtn.addEventListener("click", loadGpRecords);
applyFilter.addEventListener("click", applyFilterStatus);

// -------------------------------
// Load patient records
// -------------------------------
async function loadGpRecords() {
    const pid = gpInput.value.trim();
    if (!pid) return;

    const data = await apiGet(`/records?patientId=${pid}`);
    gpRecordsList.innerHTML = "";
    detailContent.style.display = "none";

    if (!data || data.error) {
        gpRecordsList.innerHTML = `<p class="text-danger">Failed to load records.</p>`;
        return;
    }

    currentRecords = data.records;
    renderRecordList(currentRecords);
}

// -------------------------------
// Render list with thumbnails
// -------------------------------
function renderRecordList(records) {
    gpRecordsList.innerHTML = "";
    if (records.length === 0) {
        gpRecordsList.innerHTML = "<p>No records found.</p>";
        return;
    }

    records.forEach(rec => {
        // CORRECT: use 'path' variable, not 'publicPath'
        const path = rec.blobName || rec.blobUrl.split('patient-uploads/').pop();

        const thumb = `
            <div class="media-thumb-small">
                <img src="${API_BASE}/media/${path}"
                     class="thumb-img"
                     onerror="this.src='img/file-icon.png'"
                     alt="thumbnail">
            </div>
        `;

        const badgeClass = {
            pending: "status-pending",
            under_review: "status-under_review",
            reviewed: "status-reviewed",
            action_required: "status-action_required"
        }[rec.status] || "status-pending";

        const row = document.createElement("div");
        row.className = "record-row";
        row.id = `row-${rec.id}`;
        row.innerHTML = `
            <div class="d-flex align-items-center">
                ${thumb}
                <div class="ms-2 flex-grow-1">
                    <strong>${rec.originalName}</strong><br>
                    <span class="small text-muted">${new Date(rec.createdAt * 1000).toLocaleString()}</span>
                </div>
                <span class="status-badge ${badgeClass}">${rec.status.replace(/_/g, ' ')}</span>
            </div>
        `;
        row.onclick = () => selectRecord(rec);
        gpRecordsList.appendChild(row);
    });
}

// -------------------------------
// Select record → show detail panel
// -------------------------------
function selectRecord(rec) {
    selectedRecord = rec;
    document.querySelectorAll(".record-row").forEach(r => r.classList.remove("selected-row"));
    document.getElementById(`row-${rec.id}`).classList.add("selected-row");

    detailContent.style.display = "block";
    detailFile.textContent = rec.originalName;
    detailDate.textContent = new Date(rec.createdAt * 1000).toLocaleString();
    detailStatus.value = rec.status;
    detailNotes.value = rec.gpNotes || "";
    detailMsg.textContent = "";
}

// -------------------------------
// Save / Delete
// -------------------------------
saveDetail.addEventListener("click", async () => {
    if (!selectedRecord) return;
    detailMsg.textContent = "Saving...";
    const res = await apiPut(`/record/${selectedRecord.id}`, {
        status: detailStatus.value,
        gpNotes: detailNotes.value
    });
    detailMsg.textContent = res && !res.error ? "Saved!" : "Error saving";
    setTimeout(() => detailMsg.textContent = "", 2000);
    loadGpRecords();
});

deleteDetail.addEventListener("click", async () => {
    if (!selectedRecord || !confirm("Permanently delete this record?")) return;
    const res = await apiDelete(`/record/${selectedRecord.id}`);
    if (!res.error) {
        detailContent.style.display = "none";
        loadGpRecords();
    }
});

// -------------------------------
// Filter
// -------------------------------
function applyFilterStatus() {
    const status = filterStatus.value;
    const filtered = status ? currentRecords.filter(r => r.status === status) : currentRecords;
    renderRecordList(filtered);
}