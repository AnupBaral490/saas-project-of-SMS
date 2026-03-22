from django.contrib import admin
from .models import Notification, NotificationRead
from accounts.models import User

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'priority', 'sender', 'created_at')
    search_fields = ('title', 'message', 'sender__username')
    list_filter = ('notification_type', 'priority', 'send_email', 'created_at')
    date_hierarchy = 'created_at'
    filter_horizontal = ('recipients',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sender":
            # Only show admin users in the sender dropdown
            kwargs["queryset"] = User.objects.filter(user_type='admin')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'read_at')
    search_fields = ('notification__title', 'user__username')
    list_filter = ('read_at',)
    date_hierarchy = 'read_at'