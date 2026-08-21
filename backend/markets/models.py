from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Market(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_RESOLVED = 'resolved'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_OPEN, 'Open'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_markets')
    winning_outcome = models.ForeignKey('Outcome', null=True, blank=True, on_delete=models.SET_NULL, related_name='won_markets')

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title


class Outcome(models.Model):
    market = models.ForeignKey(Market, related_name='outcomes', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # e.g., "YES", "NO"
    current_price = models.DecimalField(max_digits=5, decimal_places=4, default=0.50)
    pool_balance = models.DecimalField(max_digits=20, decimal_places=4, default=0.0)  # Liquidity pool balance

    def __str__(self) -> str:
        return f"{self.market.title} - {self.name}"


class Position(models.Model):
    user = models.ForeignKey('auth.User', related_name='positions', on_delete=models.CASCADE)
    outcome = models.ForeignKey(Outcome, related_name='positions', on_delete=models.CASCADE)
    shares = models.DecimalField(max_digits=20, decimal_places=4, default=0.0)

    class Meta:
        unique_together = ('user', 'outcome')

    def __str__(self) -> str:
        return f"{self.user.username} - {self.shares} shares of {self.outcome}"


class Comment(models.Model):
    """Comment on a market for discussion."""
    market = models.ForeignKey(Market, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', related_name='comments', on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} on {self.market.title}: {self.text[:50]}"


class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=1000.00)

    def __str__(self):
        return f"{self.user.username}'s Profile ($ {self.balance})"


class Source(models.Model):
    TYPE_YOUTUBE = 'youtube'
    TYPE_ARTICLE = 'article'
    TYPE_PODCAST = 'podcast'

    TYPE_CHOICES = [
        (TYPE_YOUTUBE, 'YouTube'),
        (TYPE_ARTICLE, 'Article'),
        (TYPE_PODCAST, 'Podcast'),
    ]

    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_READY = 'ready'
    STATUS_NEEDS_REVIEW = 'needs_review'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_READY, 'Ready'),
        (STATUS_NEEDS_REVIEW, 'Needs review'),
        (STATUS_FAILED, 'Failed'),
    ]

    source_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_YOUTUBE)
    url = models.URLField(max_length=1000, unique=True)
    external_id = models.CharField(max_length=128, blank=True, db_index=True)
    title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='claim_sources',
    )
    metadata = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or self.url


class Document(models.Model):
    source = models.OneToOneField(Source, on_delete=models.CASCADE, related_name='document')
    content = models.TextField()
    language = models.CharField(max_length=32, blank=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    segments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Document for {self.source}'


class Claim(models.Model):
    STATUS_SUGGESTED = 'suggested'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_PUBLISHED = 'published'

    STATUS_CHOICES = [
        (STATUS_SUGGESTED, 'Suggested'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_PUBLISHED, 'Published'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='claims')
    statement = models.CharField(max_length=500)
    excerpt = models.TextField(blank=True)
    excerpt_start_seconds = models.PositiveIntegerField(null=True, blank=True)
    rationale = models.TextField(blank=True)
    resolution_criteria = models.TextField()
    resolution_source_url = models.URLField(max_length=1000)
    closes_at = models.DateTimeField()
    resolves_at = models.DateTimeField()
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0.500,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    extraction_method = models.CharField(max_length=64, default='heuristic')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SUGGESTED)
    market = models.OneToOneField(
        Market,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_claim',
    )
    reviewed_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_claims',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.statement


class Evidence(models.Model):
    STANCE_SUPPORTS = 'supports'
    STANCE_CONTRADICTS = 'contradicts'
    STANCE_CONTEXT = 'context'
    STANCE_CHOICES = [
        (STANCE_SUPPORTS, 'Supports'),
        (STANCE_CONTRADICTS, 'Contradicts'),
        (STANCE_CONTEXT, 'Context'),
    ]

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='evidence')
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=500)
    excerpt = models.TextField(blank=True)
    stance = models.CharField(max_length=16, choices=STANCE_CHOICES, default=STANCE_CONTEXT)
    content_hash = models.CharField(max_length=64, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-captured_at']


class Trade(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='trades')
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='trades')
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name='trades')
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    shares = models.DecimalField(max_digits=20, decimal_places=4)
    price_before = models.DecimalField(max_digits=5, decimal_places=4)
    price_after = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ForecastSnapshot(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='forecasts')
    user = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='forecast_snapshots',
    )
    agent_name = models.CharField(max_length=128, blank=True)
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    rationale = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ResolutionProposal(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name='resolution_proposals')
    proposed_outcome = models.ForeignKey(Outcome, null=True, on_delete=models.SET_NULL)
    proposed_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    proposer_agent = models.CharField(max_length=128, blank=True)
    rationale = models.TextField()
    evidence_urls = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


class ForecasterScore(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='forecaster_score')
    predictions = models.PositiveIntegerField(default=0)
    brier_score = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    log_score = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    updated_at = models.DateTimeField(auto_now=True)

# Signals to auto-create UserProfile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
