const uploadForm = document.getElementById("uploadForm");
const patientId = document.getElementById("patientId");
const fileInput = document.getElementById("fileInput");
const refreshBtn = document.getElementById("refreshBtn");
const recordsList = document.getElementById("recordsList");
const msg = document.getElementById("msg");
const progressBar = document.querySelector(".progress");
const bar = progressBar.querySelector(".progress-bar");

uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!patientId.value.trim() || !fileInput.files[0]) {
        msg.textContent = "Please enter Patient ID and select a file.";
        return;
    }

    msg.textContent = "Uploading...";
    progressBar.style.display = "block";
    bar.style.width = "0%";

    const fd = new FormData();
    fd.append("patientId", patientId.value.trim());
    fd.append("file", fileInput.files[0]);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload`);
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            bar.style.width = `${percent}%`;
        }
    };
    xhr.onload = () => {
        progressBar.style.display = "none";
        if (xhr.status >= 200 && xhr.status < 300) {
            msg.textContent = "Upload successful!";
            fileInput.value = "";
            loadRecords();
        } else {
            msg.textContent = "Upload failed.";
        }
    };
    xhr.send(fd);
});

refreshBtn.addEventListener("click", loadRecords);
patientId.addEventListener("input", () => { if (patientId.value.trim()) loadRecords(); });

async function loadRecords() {
    const pid = patientId.value.trim();
    if (!pid) {
        recordsList.innerHTML = "";
        return;
    }

    const data = await apiGet(`/records?patientId=${pid}`);
    recordsList.innerHTML = "";

    if (!data || !data.records || data.records.length === 0) {
        recordsList.innerHTML = "<p>No uploads yet.</p>";
        return;
    }

    data.records.forEach(rec => {
        // CORRECT: use 'path', not 'publicPath'
        const path = rec.blobName || rec.blobUrl.split('patient-uploads/').pop();

        const isImage = rec.contentType && rec.contentType.startsWith("image/");
        const preview = isImage
            ? `<img src="${API_BASE}/media/${path}" class="preview-img" onerror="this.src='img/file-icon.png'" alt="preview">`
            : `<img src="img/file-icon.png" class="preview-img" alt="file">`;

        const card = document.createElement("div");
        card.className = "col-12 col-md-6 col-lg-4";
        card.innerHTML = `
            <div class="record-card d-flex">
                ${preview}
                <div class="ms-3 flex-grow-1">
                    <div><strong>${rec.originalName}</strong></div>
                    <div class="small text-muted">Uploaded: ${new Date(rec.createdAt * 1000).toLocaleString()}</div>
                    <div><span class="status-badge status-${rec.status}">${rec.status.replace(/_/g, ' ')}</span></div>
                    <a href="${API_BASE}/media/${path}" target="_blank" class="btn btn-sm btn-outline-primary mt-2">Open Full Size</a>
                </div>
            </div>
        `;
        recordsList.appendChild(card);
    });
};

// Auto-load on page open if patientId is pre-filled (optional)
if (patientId.value.trim()) loadRecords();