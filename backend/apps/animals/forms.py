from django import forms
from .models import Animal

class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = [
            'subcategory', 'identification_no', 'additional_info', 
            'gender', 'weight', 'price', 'status', 'manual_name'
        ]
        widgets = {
            'subcategory': forms.Select(attrs={'class': 'custom-input'}),
            'identification_no': forms.TextInput(attrs={'class': 'custom-input', 'placeholder': 'İdentifikasiya No'}),
            'additional_info': forms.Textarea(attrs={'class': 'custom-input', 'placeholder': 'Əlavə məlumat', 'rows': 3}),
            'gender': forms.Select(attrs={'class': 'custom-input'}),
            'weight': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Çəki (kq)'}),
            'price': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Qiymət (AZN)'}),
            'status': forms.Select(attrs={'class': 'custom-input'}),
        }
