from django import forms
from .models import Seed

class SeedForm(forms.ModelForm):
    class Meta:
        model = Seed
        fields = ['name', 'quantity', 'unit', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Miqdar', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qiymət (AZN)', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'unit': forms.Select(attrs={'class': 'form-control', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
        }
