from django.contrib import admin
from .models import Profile

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'surname', 'nickname', 'is_teacher')
    search_fields = ('user__username', 'nickname')
    list_filter = ('nickname', 'is_teacher')
    
admin.site.register(Profile, ProfileAdmin)
