from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem, Client, BusinessProfile


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
