let currentJobId = null;
let statusCheckInterval = null;

document.getElementById('file').addEventListener('change', function(e) {
    const fileName = e.target.files[0]?.name;
    const fileNameDiv = document.getElementById('file-name');
    if (fileName) {
        fileNameDiv.textContent = `Selected: ${fileName}`;
        fileNameDiv.style.display = 'block';
    } else {
        fileNameDiv.style.display = 'none';
    }
});

document.getElementById('upload-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    // Disable button and show loading
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';
    
    // Hide previous sections
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        currentJobId = data.job_id;
        
        // Show progress section
        document.getElementById('upload-section').style.display = 'none';
        document.getElementById('progress-section').style.display = 'block';
        
        // Start polling for status
        startStatusCheck();
        
    } catch (error) {
        showError(error.message);
        resetButton();
    }
});

function startStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    statusCheckInterval = setInterval(async () => {
        if (!currentJobId) return;
        
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Status check failed');
            }
            
            updateProgress(data.progress, data.message);
            
            if (data.status === 'completed') {
                clearInterval(statusCheckInterval);
                showResults(data.result);
            } else if (data.status === 'error') {
                clearInterval(statusCheckInterval);
                showError(data.error || 'Analysis failed');
            }
            
        } catch (error) {
            clearInterval(statusCheckInterval);
            showError(error.message);
        }
    }, 2000); // Check every 2 seconds
}

function updateProgress(progress, message) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressMessage = document.getElementById('progress-message');
    
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${progress}%`;
    progressMessage.textContent = message;
}

function showResults(result) {
    const resultsSection = document.getElementById('results-section');
    const resultsSummary = document.getElementById('results-summary');
    const downloadBtn = document.getElementById('download-btn');
    const viewBtn = document.getElementById('view-btn');
    
    // Build summary HTML
    resultsSummary.innerHTML = `
        <h3>📊 Analysis Summary</h3>
        <p><strong>Company:</strong> ${result.company_name}</p>
        <p><strong>Verification Score:</strong> ${(result.verification_score * 100).toFixed(1)}%</p>
        <p><strong>Claims Analyzed:</strong> ${result.num_claims}</p>
        <p><strong>Questions Generated:</strong> ${result.num_questions}</p>
        ${result.email_sent ? '<p style="color: green;">✓ Report sent to email</p>' : ''}
    `;
    
    // Set up download button
    downloadBtn.onclick = () => {
        window.location.href = `/download/${currentJobId}`;
    };
    
    // Set up view button
    viewBtn.onclick = () => {
        window.open(`/view/${currentJobId}`, '_blank');
    };
    
    // Show results section
    document.getElementById('progress-section').style.display = 'none';
    resultsSection.style.display = 'block';
    
    resetButton();
}

function showError(message) {
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    document.getElementById('progress-section').style.display = 'none';
    errorSection.style.display = 'block';
    
    resetButton();
}

function resetButton() {
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    
    submitBtn.disabled = false;
    btnText.style.display = 'inline';
    btnLoader.style.display = 'none';
}

function cancelAndReset() {
    // Stop status checking
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    
    // Reset form
    resetForm();
}

function resetForm() {
    document.getElementById('upload-form').reset();
    document.getElementById('file-name').style.display = 'none';
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
    
    // Reset progress bar
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-text').textContent = '0%';
    document.getElementById('progress-message').textContent = 'Starting analysis...';
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    
    currentJobId = null;
    resetButton();
}
