from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import Invoice, InvoiceItem, Client, BusinessProfile


class MarkAsPaidForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=Invoice.PAYMENT_METHOD_CHOICES,
        widget=forms.Select()
    )
    amount_received = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'placeholder': '0.00',
        })
    )
    paid_at = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        )
    )
    payment_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Transaction ID, cheque no., etc. (optional)'
        })
    )

    def __init__(self, *args, **kwargs):
        invoice_total = kwargs.pop('invoice_total', None)
        super().__init__(*args, **kwargs)
        now = timezone.localtime(timezone.now())
        self.fields['paid_at'].initial = now.strftime('%Y-%m-%dT%H:%M')
        if invoice_total is not None:
            self.fields['amount_received'].initial = invoice_total


class ClientForm(forms.ModelForm):
    class Meta:
        model  = Client
        fields = [
            'name', 'company_name', 'email', 'phone',
            'address_line1', 'address_line2', 'city', 'state', 'country',
            'notes'
        ]
        widgets = {
            'name':          forms.TextInput(attrs={'placeholder': 'Full name'}),
            'company_name':  forms.TextInput(attrs={'placeholder': 'Company name (optional)'}),
            'email':         forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'phone':         forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street address'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Apt, suite, etc. (optional)'}),
            'city':          forms.TextInput(attrs={'placeholder': 'City'}),
            'state':         forms.TextInput(attrs={'placeholder': 'State'}),
            'country':       forms.TextInput(attrs={'placeholder': 'Country'}),
            'notes':         forms.Textarea(attrs={'placeholder': 'Internal notes...', 'rows': 3}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model  = Invoice
        fields = ['client', 'issue_date', 'due_date', 'tax_rate', 'notes']
        widgets = {
            'client':     forms.Select(),
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date':   forms.DateInput(attrs={'type': 'date'}),
            'tax_rate':   forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'notes':      forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes for the client...'}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model  = InvoiceItem
        fields = ['description', 'quantity', 'unit_price', 'order']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Service or product description'}),
            'quantity':    forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '1'}),
            'unit_price':  forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'order':       forms.HiddenInput(),
        }


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model  = BusinessProfile
        fields = [
            'name', 'tagline', 'logo',
            'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
            'phone', 'email', 'website',
            'tax_id',
            'bank_name', 'account_name', 'account_number',
            'invoice_footer_note', 'receipt_footer_note',
        ]
        widgets = {
            'name':                forms.TextInput(attrs={'placeholder': 'Your Business Name Ltd.'}),
            'tagline':             forms.TextInput(attrs={'placeholder': 'Your business tagline (optional)'}),
            'logo':                forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
            'address_line1':       forms.TextInput(attrs={'placeholder': 'Street address'}),
            'address_line2':       forms.TextInput(attrs={'placeholder': 'Apartment, suite, floor (optional)'}),
            'city':                forms.TextInput(attrs={'placeholder': 'City'}),
            'state':               forms.TextInput(attrs={'placeholder': 'State / Province'}),
            'country':             forms.TextInput(attrs={'placeholder': 'Country'}),
            'postal_code':         forms.TextInput(attrs={'placeholder': 'Postal / ZIP code'}),
            'phone':               forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'email':               forms.EmailInput(attrs={'placeholder': 'business@example.com'}),
            'website':             forms.URLInput(attrs={'placeholder': 'https://yourwebsite.com'}),
            'tax_id':              forms.TextInput(attrs={'placeholder': 'RC number, TIN, or VAT ID'}),
            'bank_name':           forms.TextInput(attrs={'placeholder': 'First Bank Nigeria'}),
            'account_name':        forms.TextInput(attrs={'placeholder': 'Your Business Name'}),
            'account_number':      forms.TextInput(attrs={'placeholder': '0123456789'}),
            'invoice_footer_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Thank you for your business.'}),
            'receipt_footer_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Payment received. Thank you.'}),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    fields=['description', 'quantity', 'unit_price', 'order'],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
