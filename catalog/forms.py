from django import forms
from .models import Brand, Collection

class BrowseForm(forms.Form):
    q = forms.CharField(required=False, max_length=120, label='Search', widget=forms.TextInput(attrs={'placeholder': 'Search watches, styles, brands…'}))
    collection = forms.ModelChoiceField(Collection.objects.all(), to_field_name='slug', required=False, empty_label='All collections')
    brand = forms.ModelChoiceField(Brand.objects.all(), to_field_name='slug', required=False, empty_label='All brands')
    min_price = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label='Min price (PKR)')
    max_price = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label='Max price (PKR)')
    strap = forms.CharField(required=False, max_length=80, label='Strap material')
    movement = forms.CharField(required=False, max_length=80, label='Movement type')
    availability = forms.ChoiceField(required=False, choices=[('', 'Any availability'), ('in_stock', 'In stock'), ('out_of_stock', 'Out of stock')])
    sort = forms.ChoiceField(required=False, choices=[('newest', 'Latest arrivals'), ('price_asc', 'Price: low to high'), ('price_desc', 'Price: high to low'), ('name', 'Name: A–Z')])

    def clean(self):
        data = super().clean()
        if data.get('min_price') is not None and data.get('max_price') is not None and data['min_price'] > data['max_price']:
            raise forms.ValidationError('Minimum price must be less than the maximum price.')
        return data
