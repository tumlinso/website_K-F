from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Contact
        fields = ['name', 'email', 'message']

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_message(self):
        return self.cleaned_data['message'].strip()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('website'):
            raise forms.ValidationError('Sicherheitsprüfung fehlgeschlagen.')

        return cleaned_data
