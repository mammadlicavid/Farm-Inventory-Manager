from django import forms
from .models import Alet

class AletForm(forms.ModelForm):
    class Meta:
        model = Alet
        fields = ['name', 'quantity', 'price', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Miqdar', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qiymət (AZN)', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'type': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
        }
