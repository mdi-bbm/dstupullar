from django.contrib import admin

from django.contrib import admin
from .models import Users

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')

admin.site.register(Users, UserAdmin)
