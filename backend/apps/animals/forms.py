from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Animal

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = [
            'subcategory', 'identification_no', 'additional_info', 
            'gender', 'weight', 'price', 'quantity', 'manual_name'
        ]
        widgets = {
            'subcategory': forms.Select(attrs={'class': 'custom-input'}),
            'identification_no': forms.TextInput(attrs={'class': 'custom-input', 'placeholder': _('İdentifikasiya No')}),
            'additional_info': forms.Textarea(attrs={'class': 'custom-input', 'placeholder': _('Əlavə məlumat'), 'rows': 3}),
            'gender': forms.Select(attrs={'class': 'custom-input'}),
            'weight': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': _('Çəki (kq)')}),
            'price': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': _('Qiymət (AZN)')}),
            'quantity': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': _('Miqdar')}),
        }
