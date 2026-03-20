from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import Membership, Class, Contact, NewsPost


def home(request):
    """Home page"""
    memberships = Membership.objects.filter(is_active=True)
    classes = Class.objects.all()
    recent_posts = NewsPost.objects.filter(is_published=True)[:2]
    context = {
        'memberships': memberships,
        'classes': classes,
        'recent_posts': recent_posts,
    }
    return render(request, 'gym_app/home.html', context)


def memberships(request):
    """Memberships page"""
    memberships = Membership.objects.filter(is_active=True)
    context = {'memberships': memberships}
    return render(request, 'gym_app/memberships.html', context)


def classes(request):
    """Classes page"""
    classes = Class.objects.all()
    context = {'classes': classes}
    return render(request, 'gym_app/classes.html', context)


@require_http_methods(["GET", "POST"])
def contact(request):
    """Contact page with form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        
        if name and email and message_text:
            # Save contact to database
            contact_obj = Contact.objects.create(
                name=name,
                email=email,
                message=message_text
            )
            
            # Send email to gym admin
            admin_email = settings.DEFAULT_FROM_EMAIL
            try:
                send_mail(
                    subject=f'Neue Kontaktanfrage von {name}',
                    message=f'Name: {name}\nEmail: {email}\n\nNachricht:\n{message_text}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=False,
                )
                
                # Send confirmation email to user
                send_mail(
                    subject='Ihre Anfrage bei K+F Fitnessstudio',
                    message=f'Hallo {name},\n\nVielen Dank für Ihre Anfrage. Wir werden Ihre Nachricht in Kürze bearbeiten und uns mit Ihnen in Verbindung setzen.\n\nBeste Grüße\nK+F Fitnessstudio Team',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Vielen Dank! Ihre Nachricht wurde erfolgreich versendet. Wir werden Ihnen in Kürze antworten.')
            except Exception as e:
                messages.warning(request, f'Nachricht gespeichert, aber E-Mail konnte nicht versendet werden: {str(e)}')
            
            return redirect('contact')
        else:
            messages.error(request, 'Bitte füllen Sie alle Felder aus.')
    
    return render(request, 'gym_app/contact.html')


def about(request):
    """About page"""
    return render(request, 'gym_app/about.html')


def entdecken(request):
    """Entdecken page"""
    return render(request, 'gym_app/entdecken.html')


def oeffnungszeiten(request):
    """Opening hours page"""
    return render(request, 'gym_app/oeffnungszeiten.html')


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
