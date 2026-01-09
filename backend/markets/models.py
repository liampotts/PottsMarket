from django.db import models


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

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=1000.00)

    def __str__(self):
        return f"{self.user.username}'s Profile ($ {self.balance})"

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
