from django.db import models
from django.utils import timezone


class Membership(models.Model):
    """Membership plan"""
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    features = models.TextField(help_text="Features separated by newlines")
    is_active = models.BooleanField(default=True)

    @property
    def feature_list(self):
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    @property
    def frequency_label(self):
        frequency_labels = {
            'monthly': 'Monat',
            'annual': 'Jahr',
        }
        return frequency_labels.get(self.frequency, self.frequency)

    @property
    def detail_url_name(self):
        detail_routes = {
            'probemonat': 'probemonat',
            'mitgliedschaft': 'mitgliedschaft',
            'monatskarte': 'monatskarte',
        }
        return detail_routes.get(self.name.strip().lower(), 'memberships')

    def __str__(self):
        return f"{self.name} - ${self.price}/{self.frequency}"


class Class(models.Model):
    """Fitness class"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    instructor = models.CharField(max_length=100)
    schedule_day = models.CharField(max_length=20)  # e.g., "Monday"
    schedule_time = models.TimeField()
    duration_minutes = models.IntegerField()
    max_participants = models.IntegerField()
    
    def __str__(self):
        return f"{self.name} - {self.schedule_day} at {self.schedule_time}"


class Contact(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message from {self.name} - {self.created_at.strftime('%Y-%m-%d')}"


class NewsPost(models.Model):
    """Neuigkeiten blog post"""
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Neuigkeit'
        verbose_name_plural = 'Neuigkeiten'

    def __str__(self):
        return self.title
