from django.contrib import admin
from .models import ChatMessage, ConnectionRequest

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'short_message', 'timestamp')
    list_filter = ('sender', 'receiver', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'message')
    ordering = ('-timestamp',)

    def short_message(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    short_message.short_description = 'Message'


@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'is_accepted', 'connection_active', 'timestamp')
    list_filter = ('is_accepted', 'connection_active', 'timestamp', 'sender', 'receiver')
    search_fields = ('sender__username', 'receiver__username')
    ordering = ('-timestamp',)
