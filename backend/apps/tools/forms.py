from django import forms
from .models import Tool, ToolCategory, ToolItem
from common.category_order import (
    TOOL_CATEGORY_ORDER,
    TOOL_ITEM_ORDER,
    order_queryset_by_name_list,
)

class ToolForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=order_queryset_by_name_list(
            ToolCategory.objects.all(),
            TOOL_CATEGORY_ORDER,
        ),
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
                category = ToolCategory.objects.filter(id=category_id).first()
                items_qs = ToolItem.objects.filter(category_id=category_id)
                if category:
                    items_qs = order_queryset_by_name_list(
                        items_qs,
                        TOOL_ITEM_ORDER.get(category.name, []),
                    )
                self.fields['item'].queryset = items_qs
            except (ValueError, TypeError):
                self.fields['item'].queryset = ToolItem.objects.none()
        elif self.instance.pk and self.instance.item:
            self.fields['category'].initial = self.instance.item.category
            items_qs = ToolItem.objects.filter(category=self.instance.item.category)
            items_qs = order_queryset_by_name_list(
                items_qs,
                TOOL_ITEM_ORDER.get(self.instance.item.category.name, []),
            )
            self.fields['item'].queryset = items_qs
        else:
            self.fields['item'].queryset = ToolItem.objects.none()
