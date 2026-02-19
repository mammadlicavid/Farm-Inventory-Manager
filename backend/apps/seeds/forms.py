from django import forms
from .models import Seed, SeedCategory, SeedItem

class SeedForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=SeedCategory.objects.all(),
        label="Kateqoriya",
        widget=forms.Select(attrs={'class': 'custom-input'}),
        required=True
    )

    class Meta:
        model = Seed
        fields = ['item', 'quantity', 'unit', 'price', 'manual_name', 'additional_info']
        widgets = {
            'item': forms.Select(attrs={'class': 'custom-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Miqdar'}),
            'unit': forms.Select(attrs={'class': 'custom-input'}),
            'price': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Qiymət (₼)'}),
            'manual_name': forms.TextInput(attrs={'class': 'custom-input', 'placeholder': 'Toxumun adı (Digər)'}),
            'additional_info': forms.Textarea(attrs={'class': 'custom-input', 'placeholder': 'Əlavə məlumat', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['item'].queryset = SeedItem.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.item:
            self.fields['category'].initial = self.instance.item.category
            self.fields['item'].queryset = self.instance.item.category.items.order_by('name')
