// static/admin/js/availability_form.js

document.addEventListener("DOMContentLoaded", function() {
    // اطمینان حاصل می‌کنیم که این کد فقط در صفحه افزودن/ویرایش Availability اجرا می‌شود
 if (window.location.pathname.includes('/admin/pricing/availability/') || 
        window.location.pathname.includes('/admin/pricing/price/')) {
        const hotelSelect = document.querySelector("#id_hotel");
        const roomTypeSelect = document.querySelector("#id_room_type");
        // URL برای API که در جنگو ساختیم
        const url = `/pricing/api/get-rooms/`;

        hotelSelect.addEventListener("change", function() {
            const hotelId = this.value;

            // اگر هتلی انتخاب نشده بود، لیست اتاق‌ها را خالی کن
            if (!hotelId) {
                roomTypeSelect.innerHTML = '<option value="">---------</option>';
                return;
            }

            // فراخوانی API با استفاده از Fetch
            fetch(`${url}${hotelId}/`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Rooms received:", data); // لاگ برای دیباگ
        roomTypeSelect.innerHTML = '<option value="">---------</option>';
        if (data.length === 0) {
            alert('هیچ اتاقی برای این هتل یافت نشد.');
        }
        data.forEach(function(room) {
            const option = new Option(room.name, room.id);
            roomTypeSelect.appendChild(option);
        });
    })
    .catch(error => {
        console.error('Error fetching rooms:', error);
        alert('خطایی در بارگذاری اتاق‌ها رخ داد.');
    });
        });
    }
});