// Real-time dynamic business validation helpers

document.addEventListener('DOMContentLoaded', function() {
    // 1. Phone number validation pattern (10 to 15 digits)
    const phoneInputs = document.querySelectorAll('input[name="phone"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            const cleaned = this.value.replace(/[\s\-\(\)\+]/g, '');
            if (cleaned.length > 0 && (!/^\d+$/.test(cleaned) || cleaned.length < 10 || cleaned.length > 15)) {
                this.setCustomValidity("Please enter a valid phone number (10 to 15 digits).");
            } else {
                this.setCustomValidity("");
            }
        });
    });

    // 2. Opportunity Amount validation (> 0)
    const amountInputs = document.querySelectorAll('input[name="amount"]');
    amountInputs.forEach(input => {
        input.addEventListener('input', function() {
            const val = parseFloat(this.value);
            if (isNaN(val) || val <= 0) {
                this.setCustomValidity("Opportunity Amount must be greater than 0.");
            } else {
                this.setCustomValidity("");
            }
        });
    });

    // 3. Probability validation (0 to 100)
    const probInputs = document.querySelectorAll('input[name="probability"]');
    probInputs.forEach(input => {
        input.addEventListener('input', function() {
            const val = parseInt(this.value, 10);
            if (isNaN(val) || val < 0 || val > 100) {
                this.setCustomValidity("Probability must be between 0 and 100.");
            } else {
                this.setCustomValidity("");
            }
        });
    });

    // 4. Expected Close Date validation (cannot be in the past for active deals)
    const closeDateInput = document.querySelector('input[name="expected_close_date"]');
    const stageSelect = document.querySelector('select[name="stage"]');
    if (closeDateInput) {
        const validateCloseDate = () => {
            if (stageSelect && (stageSelect.value === 'Won' || stageSelect.value === 'Lost')) {
                closeDateInput.setCustomValidity("");
                return;
            }
            if (closeDateInput.value) {
                const today = new Date().toISOString().split('T')[0];
                if (closeDateInput.value < today) {
                    closeDateInput.setCustomValidity("Expected Close Date cannot be in the past.");
                } else {
                    closeDateInput.setCustomValidity("");
                }
            }
        };
        closeDateInput.addEventListener('change', validateCloseDate);
        if (stageSelect) stageSelect.addEventListener('change', validateCloseDate);
    }

    // 5. Follow-Up Date validation (cannot be in the past for new/planned)
    const followupDateInput = document.querySelector('input[name="followup_date"], input[name="new_followup_date"]');
    const followupStatusSelect = document.querySelector('select[name="status"]');
    if (followupDateInput) {
        const validateFollowupDate = () => {
            if (followupStatusSelect && followupStatusSelect.value !== 'Planned') {
                followupDateInput.setCustomValidity("");
                return;
            }
            if (followupDateInput.value) {
                const today = new Date().toISOString().split('T')[0];
                if (followupDateInput.value < today) {
                    followupDateInput.setCustomValidity("Follow-up date cannot be earlier than today.");
                } else {
                    followupDateInput.setCustomValidity("");
                }
            }
        };
        followupDateInput.addEventListener('change', validateFollowupDate);
        if (followupStatusSelect) followupStatusSelect.addEventListener('change', validateFollowupDate);
    }
});

