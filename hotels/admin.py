# hotels/admin.py

from django.contrib import admin
from .models import City, Amenity, Hotel, RoomType,BoardType

admin.site.register(City)
admin.site.register(Amenity)
admin.site.register(Hotel)
admin.site.register(RoomType)
@admin.register(BoardType)
class BoardTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')