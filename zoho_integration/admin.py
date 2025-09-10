from django.contrib import admin
from .models import ProcessedPhone

@admin.register(ProcessedPhone)
class ProcessedPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'owner', 'created_at')  # Columns to display in admin list view
    list_filter = ('owner', 'created_at')  # Filters for sidebar
    search_fields = ('phone_number', 'owner')  # Searchable fields
    ordering = ('-created_at',)  # Sort by created_at (newest first)
    readonly_fields = ('created_at',)  # Make created_at read-only

    def has_add_permission(self, request):
        return False  # Disable adding new records manually in admin

    def has_delete_permission(self, request, obj=None):
        return True  # Allow deleting records

    def has_change_permission(self, request, obj=None):
        return True  # Allow editing records
