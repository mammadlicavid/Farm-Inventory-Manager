from django.contrib import admin
from .models import Animal, AnimalCategory, AnimalSubCategory

@admin.register(AnimalCategory)
class AnimalCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(AnimalSubCategory)
class AnimalSubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)

@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('subcategory', 'identification_no', 'gender', 'status', 'created_at')
    list_filter = ('status', 'gender', 'subcategory__category')
    search_fields = ('identification_no', 'breed', 'subcategory__name')
