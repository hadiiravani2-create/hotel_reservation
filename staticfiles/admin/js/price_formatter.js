// static/admin/js/price_formatter.js
// version: 0.0.1
// Note: Updated to target 'price_per_night' in addition to fields ending in 'price'.

(function($) {
    'use strict';

    /**
     * Formats a number string with non-breaking space as a thousand separator.
     * @param {string} numStr - The number string to format.
     * @returns {string} - The formatted number string.
     */
    function formatNumber(numStr) {
        if (!numStr) return '';
        // Remove all non-digit characters
        let cleanStr = numStr.replace(/[^\d]/g, '');
        
        // Use regex to add non-breaking space (\xa0) as thousand separator
        // This separator is consistent with our Farsi locale override (formats.py)
        return cleanStr.replace(/\B(?=(\d{3})+(?!\d))/g, '\xa0');
    }

    /**
     * Attaches the real-time formatting logic to a specific jQuery selector.
     * @param {string} selector - The jQuery selector for the input field(s).
     */
    function initPriceFormatter(selector) {
        // Use 'input' event to catch typing, pasting, and deleting
        $(document).on('input', selector, function(e) {
            let $input = $(this);
            let originalVal = $input.val();
            let cursorPosition = this.selectionStart;
            
            let formattedVal = formatNumber(originalVal);
            
            // Calculate how many separators were added/removed to adjust cursor
            let originalSeparators = (originalVal.substring(0, cursorPosition).match(/\xa0/g) || []).length;
            let newSeparators = (formattedVal.substring(0, cursorPosition).match(/\xa0/g) || []).length;
            let separatorDiff = newSeparators - originalSeparators;
            
            // Set the new value
            $input.val(formattedVal);
            
            // Adjust cursor position to feel natural after formatting
            this.setSelectionRange(cursorPosition + separatorDiff, cursorPosition + separatorDiff);
        });
    }

    // Wait for the DOM to be ready
    $(document).ready(function() {
        // Initialize formatting for specific admin fields based on 'pricing/admin.py'
        
        // Target fields ending with 'price' (e.g., 'extra_person_price', 'child_price')
        initPriceFormatter('input[name$="price"]');
        
        // Also target the specific 'price_per_night' field
        initPriceFormatter('input[name$="price_per_night"]');
    });

})(django.jQuery);
