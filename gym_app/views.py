import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .forms import ContactForm
from .live_status import get_home_live_status
from .models import Membership, Class, NewsPost
from .trainer_calendar import get_trainer_calendar_days, get_trainer_calendar_time_markers

logger = logging.getLogger(__name__)


def home(request):
    """Home page"""
    memberships = Membership.objects.filter(is_active=True)
    recent_posts = NewsPost.objects.filter(is_published=True)[:2]
    context = {
        'memberships': memberships,
        'recent_posts': recent_posts,
        'live_status': get_home_live_status(),
    }
    return render(request, 'gym_app/home.html', context)


def memberships(request):
    """Memberships page"""
    memberships = Membership.objects.filter(is_active=True)
    context = {'memberships': memberships}
    return render(request, 'gym_app/memberships.html', context)


def probemonat(request):
    """Probemonat detail page"""
    return render(request, 'gym_app/probemonat.html')


def mitgliedschaft(request):
    """Mitgliedschaft detail page"""
    return render(request, 'gym_app/mitgliedschaft.html')


def monatskarte(request):
    """Monatskarte detail page"""
    return render(request, 'gym_app/monatskarte.html')


def classes(request):
    """Classes page"""
    classes = Class.objects.all()
    context = {'classes': classes}
    return render(request, 'gym_app/classes.html', context)


@require_http_methods(["GET", "POST"])
def contact(request):
    """Contact page with form submission"""
    form = ContactForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            contact_obj = form.save()

            admin_message = EmailMessage(
                subject=f'Neue Kontaktanfrage von {contact_obj.name}',
                body=(
                    f'Name: {contact_obj.name}\n'
                    f'E-Mail: {contact_obj.email}\n\n'
                    f'Nachricht:\n{contact_obj.message}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_RECIPIENT_EMAIL],
                reply_to=[contact_obj.email],
            )
            confirmation_message = EmailMessage(
                subject='Ihre Anfrage bei K+F Fitnessstudio',
                body=(
                    f'Hallo {contact_obj.name},\n\n'
                    'vielen Dank fuer Ihre Anfrage. Wir haben Ihre Nachricht erhalten '
                    'und melden uns so schnell wie moeglich bei Ihnen.\n\n'
                    'Beste Gruesse\n'
                    'K+F Fitnessstudio Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[contact_obj.email],
            )

            try:
                admin_message.send(fail_silently=False)
                confirmation_message.send(fail_silently=False)
                messages.success(
                    request,
                    'Vielen Dank! Ihre Nachricht wurde erfolgreich versendet. '
                    'Wir werden Ihnen in Kuerze antworten.',
                )
            except Exception:
                logger.exception('Failed to send contact form emails for submission %s', contact_obj.pk)
                messages.warning(
                    request,
                    'Ihre Nachricht wurde gespeichert, aber die E-Mail-Zustellung ist '
                    'fehlgeschlagen. Bitte kontaktieren Sie uns direkt per E-Mail.',
                )

            return redirect('contact')

        messages.error(request, 'Bitte pruefen Sie die markierten Felder.')

    return render(request, 'gym_app/contact.html', {'form': form})


def about(request):
    """About page"""
    return render(request, 'gym_app/about.html')


def entdecken(request):
    """Entdecken page"""
    return render(request, 'gym_app/entdecken.html')


def oeffnungszeiten(request):
    """Opening hours page"""
    context = {
        'trainer_calendar_days': get_trainer_calendar_days(),
        'trainer_calendar_markers': get_trainer_calendar_time_markers(),
    }
    return render(request, 'gym_app/oeffnungszeiten.html', context)


def preise(request):
    """Preise page"""
    return render(request, 'gym_app/preise.html')


def neuigkeiten(request):
    """Neuigkeiten list page"""
    posts = NewsPost.objects.filter(is_published=True)
    return render(request, 'gym_app/neuigkeiten.html', {'posts': posts})


def neuigkeiten_detail(request, slug):
    """Single Neuigkeit page"""
    post = get_object_or_404(NewsPost, slug=slug, is_published=True)
    recent_posts = NewsPost.objects.filter(is_published=True).exclude(pk=post.pk)[:3]
    context = {
        'post': post,
        'recent_posts': recent_posts,
    }
    return render(request, 'gym_app/neuigkeiten_detail.html', context)
