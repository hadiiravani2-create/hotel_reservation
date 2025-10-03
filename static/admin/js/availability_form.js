// static/admin/js/availability_form.js
// version 2
// This comment is for versioning purposes.

// Use django.jQuery to ensure compatibility and avoid conflicts within the admin environment.
if (typeof django !== 'undefined' && typeof django.jQuery !== 'undefined') {
    (function($) {
        $(document).ready(function() {
            // Check if we are on the correct admin page for Availability or Price.
            if (!$('body').is('.change-form.app-pricing.model-availability, .change-form.app-pricing.model-price')) {
                return; // Exit if not on the correct page
            }
            
            const hotelSelect = $('#id_hotel');
            const roomTypeSelect = $('#id_room_type');
            
            // The new, dedicated URL for admin AJAX requests.
            const ajaxUrl = '/pricing/ajax/get-room-types-for-admin/';

            function updateRoomTypes() {
                const hotelId = hotelSelect.val();

                if (!hotelId) {
                    roomTypeSelect.html('<option value="">---------</option>');
                    roomTypeSelect.prop('disabled', true);
                    return;
                }

                $.ajax({
                    url: ajaxUrl,
                    data: { 'hotel_id': hotelId },
                    success: function(data) {
                        roomTypeSelect.html(''); // Clear existing options
                        roomTypeSelect.append('<option value="">---------</option>');

                        if (data && data.length > 0) {
                            $.each(data, function(index, room) {
                                roomTypeSelect.append($('<option>', {
                                    value: room.id,
                                    text: room.name
                                }));
                            });
                            roomTypeSelect.prop('disabled', false);
                        } else {
                            roomTypeSelect.html('<option value="">هیچ اتاقی برای این هتل یافت نشد</option>');
                            roomTypeSelect.prop('disabled', true);
                        }
                    },
                    error: function() {
                        console.error('Error fetching room types for admin.');
                        roomTypeSelect.html('<option value="">خطا در بارگذاری اتاق‌ها</option>');
                        roomTypeSelect.prop('disabled', true);
                    }
                });
            }

            // Bind the event and run on page load
            hotelSelect.on('change', updateRoomTypes);
            if (hotelSelect.val()) {
                // Important: We need to preserve the selected room_type value if it exists (on form error)
                const selectedRoomTypeId = roomTypeSelect.val();
                updateRoomTypes();
                // A small delay to ensure options are loaded before re-selecting
                setTimeout(function() {
                    roomTypeSelect.val(selectedRoomTypeId);
                }, 100); 
            } else {
                roomTypeSelect.prop('disabled', true);
            }
        });
    })(django.jQuery);
}
