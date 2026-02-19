from django import forms
from .models import Tool, ToolCategory, ToolItem

class ToolForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ToolCategory.objects.all(),
        label="Ana Kateqoriya",
        widget=forms.Select(attrs={'class': 'custom-input', 'id': 'id_category'}),
        required=True
    )

    class Meta:
        model = Tool
        fields = ['item', 'quantity', 'price', 'additional_info', 'manual_name']
        widgets = {
            'item': forms.Select(attrs={'class': 'custom-input', 'id': 'id_item'}),
            'quantity': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Miqdar'}),
            'price': forms.NumberInput(attrs={'class': 'custom-input', 'placeholder': 'Qiymət (₼)'}),
            'additional_info': forms.Textarea(attrs={'class': 'custom-input', 'placeholder': 'Əlavə məlumat', 'rows': 3}),
            'manual_name': forms.TextInput(attrs={'class': 'custom-input', 'placeholder': 'Alət adı (Digər)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['item'].queryset = ToolItem.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['item'].queryset = ToolItem.objects.none()
        elif self.instance.pk and self.instance.item:
            self.fields['category'].initial = self.instance.item.category
            self.fields['item'].queryset = ToolItem.objects.filter(category=self.instance.item.category).order_by('name')
        else:
            self.fields['item'].queryset = ToolItem.objects.none()
