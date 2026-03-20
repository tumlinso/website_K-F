from django.contrib import admin
from .models import Membership, Class, Contact, NewsPost


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'frequency', 'is_active')
    list_filter = ('is_active', 'frequency')


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'instructor', 'schedule_day', 'schedule_time')
    list_filter = ('schedule_day',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'updated_at')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
