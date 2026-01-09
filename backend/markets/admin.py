from django.contrib import admin

from .models import Market


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'created_at')
    search_fields = ('title', 'slug')
    list_filter = ('status',)

# Register your models here.
