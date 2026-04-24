from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'email', 'name', 'age', 'height', 'weight', 'created_at')
    search_fields = ('email', 'name')
    ordering = ('-created_at',)
