from django.contrib import admin
from .models import GuidePage

@admin.register(GuidePage)
class GuidePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'page_slug')
    prepopulated_fields = {'page_slug': ('title',)}
