from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'message']

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_message(self):
        return self.cleaned_data['message'].strip()
