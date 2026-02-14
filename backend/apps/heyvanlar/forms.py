from django import forms
from .models import Animal

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['name', 'quantity', 'weight', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Say', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Çəki (kq)', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Qiymət (AZN)', 'style': 'width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none;'}),
        }
