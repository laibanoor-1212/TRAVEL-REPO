from django.contrib import admin
from .models import GuidePage
from base.models import ContactMessage

@admin.register(GuidePage)
class GuidePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'page_slug')
    prepopulated_fields = {'page_slug': ('title',)}



@admin.register(ContactMessage)
class ContactQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'category', 'created_at', 'is_resolved')
    list_filter = ('category', 'is_resolved', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'category', 'message', 'created_at')
    list_editable = ('is_resolved',)
