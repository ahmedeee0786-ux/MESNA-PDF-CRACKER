document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('pdf_file');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const form = document.getElementById('crackForm');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result');
    const resultTitle = document.getElementById('resultTitle');
    const resultContent = document.getElementById('resultContent');
    const submitBtn = document.getElementById('submitBtn');

    // Handle Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('dragover');
        }, false);
    });

    uploadArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                fileNameDisplay.textContent = file.name;
                
                // Keep the file in the input
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
            } else {
                alert('Please upload a valid PDF file.');
                fileInput.value = '';
                fileNameDisplay.textContent = '';
            }
        }
    }

    // Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!fileInput.files.length) {
            alert('Please select a PDF file first.');
            return;
        }

        const crackMode = document.querySelector('input[name="crack_mode"]:checked').value;
        const passwordsText = document.getElementById('passwords').value.trim();
        let pinLength = 6;
        if (crackMode === 'numeric') {
            pinLength = parseInt(document.getElementById('pin_length').value);
        }
        
        if (crackMode === 'dict' && !passwordsText) {
            alert('Please provide a password dictionary.');
            return;
        }

        // Prepare UI
        submitBtn.disabled = true;
        form.classList.add('hidden');
        loading.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        resultContainer.className = 'result-container hidden';

        // Setup Live Stats
        const liveStatsEl = document.getElementById('liveStats');
        const liveTimeEl = document.getElementById('liveTime');
        const liveAttemptEl = document.getElementById('liveAttempt');
        
        liveStatsEl.classList.remove('hidden');
        liveTimeEl.textContent = "00:00:00";
        if (crackMode === 'numeric') {
            liveAttemptEl.textContent = "0".repeat(pinLength);
        } else if (crackMode === 'dob') {
            liveAttemptEl.textContent = "01011990";
        } else {
            liveAttemptEl.textContent = "DICTIONARY";
        }

        let seconds = 0;
        const timerInterval = setInterval(() => {
            seconds++;
            const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
            const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');
            liveTimeEl.textContent = `${h}:${m}:${s}`;
        }, 1000);

        let currentNum = 0;
        const liveAttemptInterval = setInterval(() => {
            if (crackMode === 'numeric') {
                // Hacker-style fast scrolling animation tailored to PIN length
                currentNum = (currentNum + Math.floor(Math.random() * 500) + 73) % (Math.pow(10, pinLength));
                liveAttemptEl.textContent = currentNum.toString().padStart(pinLength, '0');
            } else if (crackMode === 'dob') {
                // Flash random dates
                const d = Math.floor(Math.random() * 28) + 1;
                const mo = Math.floor(Math.random() * 12) + 1;
                const y = Math.floor(Math.random() * 126) + 1900;
                liveAttemptEl.textContent = `${d.toString().padStart(2,'0')}${mo.toString().padStart(2,'0')}${y}`;
            } else {
                liveAttemptEl.textContent = "DICTIONARY...";
            }
        }, 30);

        // Prepare Data
        const formData = new FormData(form);

        try {
            const response = await fetch('/crack', {
                method: 'POST',
                body: formData,
                headers: {
                    'Bypass-Tunnel-Reminder': 'true'
                }
            });

            const data = await response.json();

            // Clear Intervals
            clearInterval(timerInterval);
            clearInterval(liveAttemptInterval);

            // Update UI
            loading.classList.add('hidden');
            resultContainer.classList.remove('hidden');
            form.classList.remove('hidden');
            submitBtn.disabled = false;

            if (response.ok) {
                if (data.success) {
                    let downloadHtml = '';
                    if (data.unlocked_url) {
                        downloadHtml = `<a href="${data.unlocked_url}" class="btn-primary" style="margin-top: 1.5rem; text-decoration: none; display: inline-flex; max-width: 300px; margin-left: auto; margin-right: auto; padding: 0.75rem;"><i class="fa-solid fa-download"></i> Download Unlocked PDF</a>`;
                    }
                    resultContainer.classList.add('success');
                    resultTitle.innerHTML = '<i class="fa-solid fa-circle-check"></i> Password Cracked Successfully!';
                    resultContent.innerHTML = `
                        <div class="password-display">${data.password}</div>
                        <div class="stats">Time taken: ${data.time_taken} &bull; Attempts: ${data.attempts}</div>
                        ${downloadHtml}
                    `;
                } else {
                    resultContainer.classList.add('error');
                    resultTitle.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Opening Failed';
                    resultContent.innerHTML = `
                        <p>${data.message}</p>
                        <div class="stats">Time taken: ${data.time_taken} &bull; Attempts: ${data.attempts}</div>
                    `;
                }
            } else {
                throw new Error(data.error || 'Server error occurred');
            }
        } catch (error) {
            clearInterval(timerInterval);
            clearInterval(liveAttemptInterval);
            loading.classList.add('hidden');
            resultContainer.classList.remove('hidden');
            resultContainer.classList.add('error');
            form.classList.remove('hidden');
            submitBtn.disabled = false;
            
            resultTitle.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error Occurred';
            resultContent.innerHTML = `<p>${error.message}</p>`;
        }
    });
});
