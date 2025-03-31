// Inbox Genie - Main JS functionality
document.addEventListener('DOMContentLoaded', function() {
    const emailForm = document.getElementById('emailForm');
    const generateBtn = document.getElementById('generateBtn');
    const emailOutput = document.getElementById('emailOutput');
    const copyBtn = document.getElementById('copyBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');

    // Form submission handler
    emailForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Show loading indicator
        emailOutput.innerHTML = '';
        loadingIndicator.classList.remove('d-none');
        generateBtn.disabled = true;
        copyBtn.disabled = true;
        
        // Collect form data
        const formData = {
            name: document.getElementById('name').value,
            role: document.getElementById('role').value,
            company: document.getElementById('company').value,
            industry: document.getElementById('industry').value || '',
            linkedin_profile: document.getElementById('linkedin_profile').value || '',
            recent_activity: document.getElementById('recent_activity').value || '',
            industry_news: document.getElementById('industry_news').value || '',
            pain_points: document.getElementById('pain_points').value || ''
        };
        
        try {
            // Send data to server
            const response = await fetch('/generate-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Format and display the generated email
            emailOutput.innerHTML = formatEmailOutput(data.email);
            copyBtn.disabled = false;
        } catch (error) {
            console.error('Error:', error);
            emailOutput.innerHTML = `<div class="alert alert-danger">Error generating email. Please try again.</div>`;
        } finally {
            // Hide loading indicator
            loadingIndicator.classList.add('d-none');
            generateBtn.disabled = false;
        }
    });
    
    // Copy to clipboard functionality
    copyBtn.addEventListener('click', function() {
        // Get the text content without HTML formatting
        const emailText = emailOutput.textContent;
        
        // Use the Clipboard API to copy text
        navigator.clipboard.writeText(emailText).then(function() {
            // Visual feedback for successful copy
            emailOutput.classList.add('copy-highlight');
            
            // Change button text temporarily
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
            
            // Reset button text after 2 seconds
            setTimeout(function() {
                copyBtn.innerHTML = originalText;
                emailOutput.classList.remove('copy-highlight');
            }, 2000);
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
        });
    });
    
    // Helper function to format email output with proper spacing
    function formatEmailOutput(emailText) {
        // Replace newlines with proper HTML spacing
        return emailText.replace(/\n/g, '<br>');
    }
});
