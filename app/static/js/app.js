// AcxiomCRM Client-side scripts and validations

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle for mobile/desktop
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('sidebar-wrapper').classList.toggle('toggled');
        });
    }

    // Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Client-side HTML5 Bootstrap form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Delete Confirmation Modals
    const confirmModalEl = document.getElementById('confirmDeleteModal');
    if (confirmModalEl) {
        confirmModalEl.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const actionUrl = button.getAttribute('data-action');
            const itemName = button.getAttribute('data-name');
            const form = confirmModalEl.querySelector('#confirmDeleteForm');
            const msgEl = confirmModalEl.querySelector('#deleteItemName');
            
            form.setAttribute('action', actionUrl);
            if (msgEl) {
                msgEl.textContent = itemName || 'this record';
            }
        });
    }
});

