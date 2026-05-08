from django.contrib import admin
from .models import MaintenanceRequest, MaintenanceComment


class CommentInline(admin.TabularInline):
    model = MaintenanceComment
    extra = 0
    readonly_fields = ('author', 'created_at')


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'tenant', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('title', 'description', 'tenant__username', 'property_address')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    inlines = [CommentInline]

    fieldsets = (
        ('Request Info', {
            'fields': ('tenant', 'title', 'category', 'priority', 'description', 'image')
        }),
        ('Location', {
            'fields': ('unit_number', 'property_address')
        }),
        ('Status', {
            'fields': ('status', 'notes', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(MaintenanceComment)
class MaintenanceCommentAdmin(admin.ModelAdmin):
    list_display = ('request', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal',)