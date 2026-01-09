from django.contrib import admin

from .models import Market


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'created_at')
    search_fields = ('title', 'slug')
    list_filter = ('status',)

# Register your models here.
from .models import Outcome, Position

@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = ('market', 'name', 'current_price', 'pool_balance')
    list_filter = ('market',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'outcome', 'shares')
    list_filter = ('user', 'outcome__market')
