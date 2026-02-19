from django import forms
from .models import Expense

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select', 
                'style': 'width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #ddd; outline: none; background-color: #f9f9f9;'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input', 
                'placeholder': '0.00',
                'style': 'width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #ddd; outline: none; background-color: #f9f9f9;'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'Qısa izah...',
                'style': 'width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #ddd; outline: none; background-color: #f9f9f9;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customizing category choices to match UI "Kateqoriya seçin"
        self.fields['category'].choices = [('', 'Kateqoriya seçin')] + list(self.fields['category'].choices)[1:]
