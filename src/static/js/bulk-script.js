// Inbox Genie - Bulk Email Processing JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const bulkUploadForm = document.getElementById('bulkUploadForm');
    const csvFileInput = document.getElementById('csvFile');
    const previewCsvBtn = document.getElementById('previewCsvBtn');
    const generateBulkBtn = document.getElementById('generateBulkBtn');
    const csvPreviewContainer = document.getElementById('csvPreviewContainer');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorContainer = document.getElementById('errorContainer');
    const errorList = document.getElementById('errorList');
    const emailsAccordion = document.getElementById('emailsAccordion');
    const noEmailsMessage = document.getElementById('noEmailsMessage');
    const bulkEmailsStats = document.getElementById('bulkEmailsStats');
    const totalRecipientsCount = document.getElementById('totalRecipientsCount');
    const successfulEmailsCount = document.getElementById('successfulEmailsCount');
    const failedEmailsCount = document.getElementById('failedEmailsCount');
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    const collapseAllBtn = document.getElementById('collapseAllBtn');

    // CSV file validation
    csvFileInput.addEventListener('change', function(e) {
        // Reset UI
        csvPreviewContainer.innerHTML = '<div class="text-center py-5 text-muted"><i class="fas fa-file-csv fa-2x mb-3"></i><p>CSV preview will appear here</p></div>';
        
        if (!this.files || !this.files[0]) {
            return;
        }
        
        const file = this.files[0];
        
        // Check file type
        if (!file.name.endsWith('.csv')) {
            csvPreviewContainer.innerHTML = '<div class="alert alert-danger m-3">Please select a CSV file.</div>';
            csvFileInput.value = '';
            return;
        }
    });
    
    // Preview CSV button click handler
    previewCsvBtn.addEventListener('click', function() {
        if (!csvFileInput.files || !csvFileInput.files[0]) {
            csvPreviewContainer.innerHTML = '<div class="alert alert-warning m-3">Please select a CSV file first.</div>';
            return;
        }
        
        const file = csvFileInput.files[0];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const csvData = e.target.result;
            displayCsvPreview(csvData);
        };
        
        reader.onerror = function() {
            csvPreviewContainer.innerHTML = '<div class="alert alert-danger m-3">Error reading the file.</div>';
        };
        
        reader.readAsText(file);
    });
    
    // Helper function to display CSV preview
    function displayCsvPreview(csvData) {
        try {
            // Parse CSV
            const rows = csvData.split('\n');
            if (rows.length === 0) {
                csvPreviewContainer.innerHTML = '<div class="alert alert-warning m-3">CSV file is empty.</div>';
                return;
            }
            
            // Extract headers
            const headers = rows[0].split(',').map(header => header.trim());
            
            // Build preview table
            let tableHtml = '<table class="table table-sm table-hover border-bottom mb-0">';
            tableHtml += '<thead class="table-light"><tr>';
            
            // Add headers
            headers.forEach(header => {
                tableHtml += `<th>${header}</th>`;
            });
            tableHtml += '</tr></thead><tbody>';
            
            // Add up to 5 rows of data for preview
            const maxRows = Math.min(rows.length, 6); // 1 header + 5 data rows
            for (let i = 1; i < maxRows; i++) {
                if (rows[i].trim() === '') continue;
                
                tableHtml += '<tr>';
                const cells = parseCSVRow(rows[i]);
                cells.forEach(cell => {
                    tableHtml += `<td>${cell}</td>`;
                });
                tableHtml += '</tr>';
            }
            
            // Add ellipsis if more rows exist
            if (rows.length > 6) {
                tableHtml += '<tr><td colspan="' + headers.length + '" class="text-center text-muted">...</td></tr>';
            }
            
            tableHtml += '</tbody></table>';
            csvPreviewContainer.innerHTML = tableHtml;
        } catch (err) {
            csvPreviewContainer.innerHTML = '<div class="alert alert-danger m-3">Error parsing CSV data.</div>';
        }
    }
    
    // Parse CSV row accounting for quoted values with commas
    function parseCSVRow(row) {
        const cells = [];
        let inQuote = false;
        let currentCell = '';
        
        for (let i = 0; i < row.length; i++) {
            const char = row[i];
            
            if (char === '"' && (i === 0 || row[i-1] !== '\\')) {
                inQuote = !inQuote;
            } else if (char === ',' && !inQuote) {
                cells.push(currentCell);
                currentCell = '';
            } else {
                currentCell += char;
            }
        }
        
        if (currentCell) {
            cells.push(currentCell);
        }
        
        // Clean up quotes from the data
        return cells.map(cell => {
            const trimmed = cell.trim();
            if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
                return trimmed.substring(1, trimmed.length - 1);
            }
            return trimmed;
        });
    }
    
    // Form submission handler
    bulkUploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!csvFileInput.files || !csvFileInput.files[0]) {
            errorContainer.classList.remove('d-none');
            errorList.innerHTML = '<li>Please select a CSV file.</li>';
            return;
        }
        
        // Reset UI
        errorContainer.classList.add('d-none');
        errorList.innerHTML = '';
        emailsAccordion.innerHTML = '';
        noEmailsMessage.classList.add('d-none');
        bulkEmailsStats.classList.add('d-none');
        loadingIndicator.classList.remove('d-none');
        generateBulkBtn.disabled = true;
        downloadAllBtn.disabled = true;
        collapseAllBtn.disabled = true;
        
        const file = csvFileInput.files[0];
        const reader = new FileReader();
        
        reader.onload = async function(e) {
            const csvData = e.target.result;
            
            try {
                // Send data to server
                const response = await fetch('/process-bulk-emails', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ csv_data: csvData })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                
                // Handle errors if any
                if (!result.success && result.errors && result.errors.length > 0) {
                    displayErrors(result.errors);
                }
                
                // Display emails and stats
                displayEmails(result);
                
            } catch (error) {
                console.error('Error:', error);
                errorContainer.classList.remove('d-none');
                errorList.innerHTML = `<li>${error.message || 'Error processing emails.'}</li>`;
            } finally {
                loadingIndicator.classList.add('d-none');
                generateBulkBtn.disabled = false;
            }
        };
        
        reader.onerror = function() {
            loadingIndicator.classList.add('d-none');
            generateBulkBtn.disabled = false;
            errorContainer.classList.remove('d-none');
            errorList.innerHTML = '<li>Error reading the CSV file.</li>';
        };
        
        reader.readAsText(file);
    });
    
    // Display errors function
    function displayErrors(errors) {
        errorContainer.classList.remove('d-none');
        errorList.innerHTML = '';
        
        errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            errorList.appendChild(li);
        });
    }
    
    // Display emails function
    function displayEmails(result) {
        // Update stats
        totalRecipientsCount.textContent = result.total_recipients;
        successfulEmailsCount.textContent = result.successful_recipients;
        failedEmailsCount.textContent = result.total_recipients - result.successful_recipients;
        bulkEmailsStats.classList.remove('d-none');
        
        if (result.emails && result.emails.length > 0) {
            // Show emails
            noEmailsMessage.classList.add('d-none');
            emailsAccordion.innerHTML = '';
            
            // Create accordion items for each email
            result.emails.forEach((item, index) => {
                const recipient = item.recipient;
                const email = item.email;
                
                const accordionItem = document.createElement('div');
                accordionItem.className = 'accordion-item';
                accordionItem.innerHTML = `
                    <h2 class="accordion-header">
                        <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" data-bs-toggle="collapse" data-bs-target="#email-${index}">
                            <div class="d-flex w-100 justify-content-between align-items-center">
                                <div>
                                    <strong>${recipient.name || 'Unnamed'}</strong> - 
                                    ${recipient.role || 'No role'} at 
                                    ${recipient.company || 'No company'}
                                </div>
                                <button class="btn btn-sm btn-outline-primary copy-btn ms-2" data-index="${index}">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                        </button>
                    </h2>
                    <div id="email-${index}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" data-bs-parent="#emailsAccordion">
                        <div class="accordion-body">
                            <pre class="email-content border rounded p-3 bg-light">${email}</pre>
                        </div>
                    </div>
                `;
                
                emailsAccordion.appendChild(accordionItem);
            });
            
            // Enable buttons
            downloadAllBtn.disabled = false;
            collapseAllBtn.disabled = false;
            
            // Add event listeners for copy buttons
            document.querySelectorAll('.copy-btn').forEach(button => {
                button.addEventListener('click', function(e) {
                    e.stopPropagation(); // Prevent accordion from toggling
                    
                    const index = this.getAttribute('data-index');
                    const email = result.emails[index].email;
                    
                    // Copy to clipboard
                    navigator.clipboard.writeText(email).then(() => {
                        // Provide visual feedback
                        const originalHtml = this.innerHTML;
                        this.innerHTML = '<i class="fas fa-check"></i>';
                        
                        setTimeout(() => {
                            this.innerHTML = originalHtml;
                        }, 2000);
                    }).catch(err => {
                        console.error('Failed to copy text: ', err);
                    });
                });
            });
        } else {
            // No emails generated
            noEmailsMessage.classList.remove('d-none');
        }
    }
    
    // Download all emails
    downloadAllBtn.addEventListener('click', function() {
        // Get all visible emails
        const emails = [];
        document.querySelectorAll('.email-content').forEach(content => {
            emails.push(content.textContent);
        });
        
        if (emails.length === 0) return;
        
        // Create text file content with separator between emails
        const content = emails.join('\n\n----------------------------\n\n');
        
        // Create download link
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
        element.setAttribute('download', `inbox_genie_emails_${new Date().toISOString().slice(0,10)}.txt`);
        
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    });
    
    // Collapse all / expand all toggle
    collapseAllBtn.addEventListener('click', function() {
        const allCollapseElements = document.querySelectorAll('.accordion-collapse');
        const allButtons = document.querySelectorAll('.accordion-button');
        
        // Check if we should expand or collapse
        const shouldExpand = [...allCollapseElements].some(el => !el.classList.contains('show'));
        
        if (shouldExpand) {
            // Expand all
            allCollapseElements.forEach(el => {
                el.classList.add('show');
            });
            allButtons.forEach(btn => {
                btn.classList.remove('collapsed');
            });
            this.innerHTML = '<i class="fas fa-compress-alt me-2"></i>Collapse All';
        } else {
            // Collapse all
            allCollapseElements.forEach(el => {
                el.classList.remove('show');
            });
            allButtons.forEach(btn => {
                btn.classList.add('collapsed');
            });
            this.innerHTML = '<i class="fas fa-expand-alt me-2"></i>Expand All';
        }
    });
});
