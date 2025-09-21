# hotels/admin.py

from django.contrib import admin
from .models import City, Amenity, Hotel, RoomType

admin.site.register(City)
admin.site.register(Amenity)
admin.site.register(Hotel)
admin.site.register(RoomType)