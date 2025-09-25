// static/admin/js/multi_booking_form.js

document.addEventListener("DOMContentLoaded", function() {
    // اطمینان از اجرای کد فقط در صفحه افزودن/ویرایش رزرو
    if (!window.location.pathname.includes('/admin/reservations/booking/')) {
        return;
    }

    // ... (انتخاب المنت‌های اصلی بدون تغییر)
    const checkInInput = document.querySelector("#id_check_in");
    const checkOutInput = document.querySelector("#id_check_out");
    const userInput = document.querySelector("#id_user");
    const priceInput = document.querySelector("#id_total_price");
    const quoteApiUrl = "/pricing/api/calculate-multi-price/";

    // ایجاد دکمه محاسبه قیمت (اگر قبلا ایجاد نشده)
    let calculateButton = document.querySelector('#calculate-price-button');
    if (!calculateButton) {
        calculateButton = document.createElement('button');
        calculateButton.id = 'calculate-price-button';
        calculateButton.type = 'button';
        calculateButton.textContent = 'محاسبه قیمت رزرو';
        calculateButton.classList.add('button', 'default');
        
        if (priceInput) {
            if (priceInput.hasAttribute('readonly')) {
                 priceInput.removeAttribute('readonly');
                 priceInput.classList.add('vTextField'); 
            }
            priceInput.closest('.form-row').append(calculateButton);
        }
    }


    function updatePrice() {
        const checkIn = checkInInput.value;
        const checkOut = checkOutInput.value;

        if (!checkIn || !checkOut) {
            alert("لطفاً تاریخ‌های ورود و خروج را وارد کنید.");
            return;
        }

        const bookingRooms = [];
        // انتخاب تمام سطر‌ها (TRs) در tbody
        const formsetBody = document.querySelector('#bookingroom_set-group tbody');
        
        if (!formsetBody) {
             alert("خطا: کانتینر فرم اتاق‌ها (Inline Formset) پیدا نشد.");
             return;
        }

        // --- اصلاح اساسی انتخابگر سطر ---
        // انتخاب همه سطرها و استفاده از فیلد room_type به عنوان تنها عنصر کلیدی برای اعتبارسنجی
        const roomRows = formsetBody.querySelectorAll('tr');

        roomRows.forEach(row => {
            
            // اگر ردیف حاوی کلاس 'empty-form' باشد، آن را نادیده بگیر.
            if (row.classList.contains('empty-form') || row.style.display === 'none') {
                return;
            }

            const roomTypeInput = row.querySelector('[name$="-room_type"]');
            const boardTypeInput = row.querySelector('[name$="-board_type"]');
            const quantityInput = row.querySelector('[name$="-quantity"]');
            const extraAdultsInput = row.querySelector('[name$="-adults"]'); 
            const childrenCountInput = row.querySelector('[name$="-children"]');
            const deleteCheckbox = row.querySelector('[name$="-DELETE"]');

            // --- اعتبارسنجی سطر معتبر ---
            // ۱. فیلد roomTypeInput باید وجود داشته باشد و مقدار داشته باشد (مقداردهی شده باشد)
            if (!roomTypeInput || !roomTypeInput.value) {
                return;
            }
            
            // ۲. اگر علامت حذف خورده باشد
            if (deleteCheckbox && deleteCheckbox.checked) {
                return;
            }

            // ۳. فیلدهای باقی مانده (باید موجود باشند، در غیر این صورت اشکال ساختاری است)
            if (!boardTypeInput || !quantityInput || !extraAdultsInput || !childrenCountInput) {
                return;
            }
            
            // ۴. Quantity باید یک عدد معتبر و بزرگتر از صفر باشد
            const quantity = parseInt(quantityInput.value);
            if (isNaN(quantity) || quantity <= 0) {
                 return;
            }
            
            // استخراج داده‌ها
            const extraAdults = parseInt(extraAdultsInput.value) || 0;
            const childrenCount = parseInt(childrenCountInput.value) || 0;
            
            bookingRooms.push({
                room_type_id: parseInt(roomTypeInput.value),
                board_type_id: parseInt(boardTypeInput.value),
                quantity: quantity,
                extra_adults: extraAdults, 
                children_count: childrenCount
            });
        });

        // بررسی نهایی برای جلوگیری از ارسال Payload خالی
        if (bookingRooms.length === 0) {
            alert("لطفاً حداقل یک اتاق معتبر برای رزرو وارد کنید.");
            return;
        }
        
        const payload = {
            check_in: checkIn,
            check_out: checkOut,
            booking_rooms: bookingRooms,
            user_id: parseInt(userInput.value) || null 
        };

        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // ... (The rest of the fetch logic remains the same)
        fetch(quoteApiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                 return response.json().then(errorData => { 
                    alert(errorData.error || "خطای نامشخص در سمت سرور رخ داد.");
                    throw new Error(JSON.stringify(errorData)); 
                 });
            }
            return response.json();
        })
        .then(data => {
            if (data.total_price !== undefined) {
                priceInput.value = data.total_price;
                alert(`قیمت کل ${data.total_price} تومان با موفقیت محاسبه شد. اکنون می‌توانید رزرو را ذخیره کنید.`);
            }
        })
        .catch(error => {
            console.error("Error fetching price:", error);
            priceInput.value = 0;
        });
    }

    // افزودن event listener به دکمه
    calculateButton.addEventListener("click", updatePrice);
});

