// static/admin/js/guest_form.js

window.addEventListener("load", function() {
    // از event delegation برای مدیریت فرم‌هایی که به صورت داینامیک اضافه می‌شوند استفاده می‌کنیم
    document.body.addEventListener('change', function(e) {
        if (e.target && e.target.matches('input[type="checkbox"][name$="-is_foreign"]')) {
            toggleGuestFields(e.target);
        }
    });

    // اجرای اولیه برای فرم‌هایی که از قبل در صفحه وجود دارند
    document.querySelectorAll('input[type="checkbox"][name$="-is_foreign"]').forEach(function(checkbox) {
        toggleGuestFields(checkbox);
    });

    function toggleGuestFields(checkbox) {
        // پیدا کردن ردیف والد این چک‌باکس
        const row = checkbox.closest('.dynamic-guests');

        const nationalIdInput = row.querySelector('input[name$="-national_id"]');
        const passportInput = row.querySelector('input[name$="-passport_number"]');

        if (checkbox.checked) {
            // اگر میهمان خارجی بود
            nationalIdInput.disabled = true;
            nationalIdInput.value = '';
            passportInput.disabled = false;
        } else {
            // اگر میهمان ایرانی بود
            nationalIdInput.disabled = false;
            passportInput.disabled = true;
            passportInput.value = '';
        }
    }
});