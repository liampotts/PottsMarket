from django.contrib import admin

from .models import (
    Claim,
    Document,
    Evidence,
    ForecastSnapshot,
    ForecasterScore,
    Market,
    ResolutionProposal,
    Source,
    Trade,
)


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


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_type', 'status', 'author', 'created_by', 'created_at')
    list_filter = ('source_type', 'status')
    search_fields = ('title', 'url', 'author', 'external_id')
    readonly_fields = ('created_at', 'processed_at')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('source', 'language', 'content_hash', 'created_at')
    search_fields = ('source__title', 'content_hash')


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('statement', 'status', 'confidence', 'extraction_method', 'reviewed_by')
    list_filter = ('status', 'extraction_method')
    search_fields = ('statement', 'document__source__title')


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'claim', 'stance', 'captured_at')
    list_filter = ('stance',)


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('user', 'market', 'outcome', 'amount', 'shares', 'created_at')
    list_filter = ('market', 'outcome')
    readonly_fields = (
        'user', 'market', 'outcome', 'amount', 'shares',
        'price_before', 'price_after', 'created_at',
    )


admin.site.register(ForecastSnapshot)
admin.site.register(ResolutionProposal)
admin.site.register(ForecasterScore)
