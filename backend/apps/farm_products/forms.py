from django import forms
from .models import FarmProduct, FarmProductCategory, FarmProductItem
from common.category_order import (
    FARM_PRODUCT_CATEGORY_ORDER,
    FARM_PRODUCT_ITEM_ORDER,
    order_queryset_by_name_list,
)


class FarmProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=order_queryset_by_name_list(
            FarmProductCategory.objects.all(),
            FARM_PRODUCT_CATEGORY_ORDER,
        ),
        label="Kateqoriya",
        widget=forms.Select(attrs={"class": "custom-input"}),
        required=True,
    )

    class Meta:
        model = FarmProduct
        fields = ["item", "quantity", "unit", "price", "manual_name", "additional_info"]
        widgets = {
            "item": forms.Select(attrs={"class": "custom-input"}),
            "quantity": forms.NumberInput(attrs={"class": "custom-input", "placeholder": "Miqdar"}),
            "unit": forms.Select(attrs={"class": "custom-input"}),
            "price": forms.NumberInput(attrs={"class": "custom-input", "placeholder": "Qiymət (₼)"}),
            "manual_name": forms.TextInput(attrs={"class": "custom-input", "placeholder": "Məhsulun adı (Digər)"}),
            "additional_info": forms.Textarea(
                attrs={"class": "custom-input", "placeholder": "Əlavə məlumat", "rows": 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "category" in self.data:
            try:
                category_id = int(self.data.get("category"))
                category = FarmProductCategory.objects.filter(id=category_id).first()
                items_qs = FarmProductItem.objects.filter(category_id=category_id)
                if category:
                    items_qs = order_queryset_by_name_list(
                        items_qs,
                        FARM_PRODUCT_ITEM_ORDER.get(category.name, []),
                    )
                self.fields["item"].queryset = items_qs
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.item:
            self.fields["category"].initial = self.instance.item.category
            items_qs = self.instance.item.category.items.all()
            items_qs = order_queryset_by_name_list(
                items_qs,
                FARM_PRODUCT_ITEM_ORDER.get(self.instance.item.category.name, []),
            )
            self.fields["item"].queryset = items_qs
