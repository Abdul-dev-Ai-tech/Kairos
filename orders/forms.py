from django import forms
from django.core.validators import RegexValidator
from .models import PaymentMethod, ShippingZone
from .delivery import normalize_mobile, validate_delivery, validate_map_url

class CartForm(forms.Form):
    variant_id = forms.IntegerField(min_value=1)
    quantity = forms.IntegerField(min_value=0, max_value=99)

class ShippingQuoteForm(forms.Form):
    shipping_zone = forms.ModelChoiceField(queryset=ShippingZone.objects.filter(active=True))
    city = forms.CharField(max_length=100, initial='Lahore', widget=forms.TextInput(attrs={'readonly': 'readonly', 'autocomplete': 'address-level2'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        zones = ShippingZone.objects.filter(active=True)
        self.fields['shipping_zone'].queryset = zones.filter(pk__in=[z.pk for z in zones if z.covers('Lahore')])

    def clean_city(self):
        city = self.cleaned_data['city'].strip()
        if city.casefold() != 'lahore':
            raise forms.ValidationError('We deliver within Lahore only.')
        return 'Lahore'

    def clean(self):
        data = super().clean()
        if data.get('shipping_zone') and data.get('city') and not data['shipping_zone'].covers(data['city']):
            raise forms.ValidationError('The selected delivery zone does not cover your city.')
        return data

class CheckoutForm(ShippingQuoteForm):
    checkout_key = forms.UUIDField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=100, min_length=2, label='Full name', widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    phone = forms.CharField(max_length=30, validators=[RegexValidator(r'^\+?[\d ()-]{7,30}$', 'Enter a valid phone number.')], widget=forms.TextInput(attrs={'autocomplete': 'tel', 'inputmode': 'tel'}))
    address = forms.CharField(min_length=10, max_length=500, widget=forms.Textarea(attrs={'rows': 3, 'autocomplete': 'street-address'}))
    area = forms.CharField(min_length=2, max_length=100, label='Area / neighbourhood', widget=forms.TextInput(attrs={'placeholder': 'e.g. Johar Town, DHA, Gulberg', 'autocomplete': 'address-level3'}))
    landmark = forms.CharField(required=False, max_length=180, label='Nearby landmark (optional)')
    map_link = forms.URLField(required=False, max_length=500, label='Google Maps pin / share link (optional)', validators=[validate_map_url], widget=forms.URLInput(attrs={'placeholder': 'https://maps.app.goo.gl/…'}))
    latitude = forms.DecimalField(required=False, max_digits=10, decimal_places=7, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, max_digits=11, decimal_places=7, widget=forms.HiddenInput)
    whatsapp_opt_in = forms.BooleanField(required=False, label='Send my order confirmation and delivery updates on WhatsApp at this mobile number.')
    postal_code = forms.CharField(required=False, max_length=15, widget=forms.TextInput(attrs={'autocomplete': 'postal-code'}))
    payment_method = forms.ModelChoiceField(queryset=PaymentMethod.objects.filter(active=True), widget=forms.RadioSelect)
    notes = forms.CharField(required=False, max_length=2000, label='Order notes (optional)', widget=forms.Textarea(attrs={'rows': 3}))
    agreement = forms.BooleanField(label='I have read the shipping, returns and privacy policies.')

    def clean_phone(self):
        return normalize_mobile(self.cleaned_data['phone'])

    def clean(self):
        data = super().clean()
        if data.get('city') and data.get('area'):
            data.update(validate_delivery(data))
        return data

class CouponForm(forms.Form):
    code = forms.CharField(max_length=40, strip=True)
