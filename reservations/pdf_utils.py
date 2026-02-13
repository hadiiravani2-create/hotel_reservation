# FILE: back/reservations/pdf_utils.py
# version: 1.0.1
# FIX: Smartly determine base_url for fonts based on DEBUG setting.

from io import BytesIO
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from pathlib import Path
from django.utils.translation import gettext_lazy as _

# Import مدل‌های مورد نیاز
# Note: Using string reference or importing inside function avoids circular imports if needed, 
# but here direct import is fine if models don't import utils.
if False: # Type hinting only
    from .models import Booking

def generate_booking_confirmation_pdf(booking) -> bytes:
    """
    Generates a PDF confirmation for a given booking object
    using WeasyPrint.
    """
    
    context = {'booking': booking}
    
    # Render the HTML template to a string
    html_string = render_to_string(
        'notifications/pdf/booking_confirmation.html', 
        context
    )
    
    # --- START: Critical Fix for Font Loading ---
    # Determine the correct base_url to find static files (fonts)
    
    if settings.DEBUG:
        # In DEBUG mode, fonts are in STATICFILES_DIRS
        # We take the first directory from the list (assuming it's defined and contains fonts)
        if not settings.STATICFILES_DIRS:
             raise Exception(_("STATICFILES_DIRS must be set in DEBUG mode for PDF generation."))
        
        static_dir = str(settings.STATICFILES_DIRS[0])
        # We must convert the OS path to a 'file://' URL
        base_url = Path(static_dir).as_uri() + '/'
    else:
        # In Production (DEBUG=False), fonts are in STATIC_ROOT
        if not settings.STATIC_ROOT:
             raise Exception(_("STATIC_ROOT must be set in Production for PDF generation."))
        
        # STATIC_ROOT is usually a path string, needs to be file URI
        base_url = Path(settings.STATIC_ROOT).as_uri() + '/'
    # --- END: Critical Fix ---

    # Create the WeasyPrint HTML object
    # The base_url tells WeasyPrint where to look for relative paths
    # like 'fonts/Vazirmatn-Regular.ttf'
    html = HTML(string=html_string, base_url=base_url)
    
    # Render the PDF to bytes
    pdf_bytes = html.write_pdf()
    
    return pdf_bytes
