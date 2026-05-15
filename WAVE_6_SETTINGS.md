# WAVE 6 — Business Profile & Settings

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1–5 are complete: scaffold, models, CRUD views, PDF generation, and payment flow
are all working. This is Wave 6. Build ONLY what is specified here.

The Settings page is where the business owner configures their business identity —
the information that appears on every invoice and receipt PDF. It includes logo upload,
business name, contact info, banking details, and PDF footer notes.

---

## Objectives
- Build the Settings view and form for `BusinessProfile`
- Handle logo upload with live preview on the page
- Enforce the single-profile rule
- Add a dedicated Settings page accessible from navigation
- Add a "Preview" feature: render a sample invoice/receipt with current settings

---

## 1. Settings Form (`core/forms.py` — add this form)

Add `BusinessProfileForm` to `core/forms.py`:

```python
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
            'name':                 forms.TextInput(attrs={'placeholder': 'Your Business Name Ltd.'}),
            'tagline':              forms.TextInput(attrs={'placeholder': 'Your business tagline (optional)'}),
            'logo':                 forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
            'address_line1':        forms.TextInput(attrs={'placeholder': 'Street address'}),
            'address_line2':        forms.TextInput(attrs={'placeholder': 'Apartment, suite, floor (optional)'}),
            'city':                 forms.TextInput(attrs={'placeholder': 'City'}),
            'state':                forms.TextInput(attrs={'placeholder': 'State / Province'}),
            'country':              forms.TextInput(attrs={'placeholder': 'Country'}),
            'postal_code':          forms.TextInput(attrs={'placeholder': 'Postal / ZIP code'}),
            'phone':                forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'email':                forms.EmailInput(attrs={'placeholder': 'business@example.com'}),
            'website':              forms.URLInput(attrs={'placeholder': 'https://yourwebsite.com'}),
            'tax_id':               forms.TextInput(attrs={'placeholder': 'RC number, TIN, or VAT ID'}),
            'bank_name':            forms.TextInput(attrs={'placeholder': 'First Bank Nigeria'}),
            'account_name':         forms.TextInput(attrs={'placeholder': 'Your Business Name'}),
            'account_number':       forms.TextInput(attrs={'placeholder': '0123456789'}),
            'invoice_footer_note':  forms.Textarea(attrs={'rows': 2, 'placeholder': 'Thank you for your business.'}),
            'receipt_footer_note':  forms.Textarea(attrs={'rows': 2, 'placeholder': 'Payment received. Thank you.'}),
        }
```

---

## 2. Settings Views (`core/views.py` — add these functions)

```python
from django.views.decorators.http import require_POST


def settings_view(request):
    """
    Display and update the BusinessProfile (settings page).
    Creates the profile if it doesn't exist yet.
    """
    profile = BusinessProfile.objects.first()

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Handle logo removal if a "clear" checkbox is submitted
            if request.POST.get('clear_logo') and profile and profile.logo:
                profile.logo.delete(save=False)
                instance = form.save(commit=False)
                instance.logo = None
                instance.save()
            else:
                form.save()
            messages.success(request, "Business profile updated successfully.")
            return redirect('core:settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BusinessProfileForm(instance=profile)

    context = {
        'form':    form,
        'profile': profile,
    }
    return render(request, 'core/settings.html', context)
```

---

## 3. URL Pattern (`core/urls.py` — add this)

```python
path('settings/', views.settings_view, name='settings'),
```

Update `base.html` Settings navigation link from `href="#"` to:
```html
href="{% url 'core:settings' %}"
```

Also update the active state detection:
```html
{% if request.resolver_match.url_name == 'settings' %}active{% endif %}
```

---

## 4. Settings Template (`core/templates/core/settings.html`)

This is a single-page settings form with multiple grouped sections.
Design it like a mobile settings app — grouped cards with clear section headers.

```html
{% extends 'base.html' %}
{% load widget_tweaks %}
{% block page_title %}Settings{% endblock %}

{% block extra_head %}
<style>
  .settings-field input,
  .settings-field select,
  .settings-field textarea {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px 14px;
    color: white;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .settings-field input:focus,
  .settings-field select:focus,
  .settings-field textarea:focus {
    border-color: #10b981;
  }
  .settings-field label {
    display: block;
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
  }
  .settings-field input[type="file"] {
    padding: 8px 12px;
    cursor: pointer;
  }
</style>
{% endblock %}

{% block content %}
<form method="post" enctype="multipart/form-data" id="settings-form">
  {% csrf_token %}
  <div class="space-y-6 max-w-2xl">

    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-heading font-bold text-white">Settings</h1>
      <p class="text-slate-400 text-sm mt-1">Configure your business profile and invoice defaults</p>
    </div>

    <!-- ── BUSINESS IDENTITY ────────────────────────────────────────────── -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
      <div class="px-5 py-4 border-b border-surface-700 bg-surface-700/30">
        <h2 class="text-sm font-heading font-semibold text-white">Business Identity</h2>
        <p class="text-xs text-slate-400 mt-0.5">Appears on all invoices and receipts</p>
      </div>
      <div class="p-5 space-y-4">

        <!-- Logo Upload -->
        <div>
          <label class="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
            Business Logo
          </label>
          <div class="flex items-start gap-4">
            <!-- Current Logo Preview -->
            <div id="logo-preview-container"
                 class="w-20 h-20 rounded-2xl overflow-hidden bg-surface-700 border-2 border-surface-600 flex items-center justify-center flex-shrink-0">
              {% if profile and profile.logo %}
                <img id="logo-preview" src="{{ profile.logo.url }}" alt="Logo"
                     class="w-full h-full object-contain" />
              {% else %}
                <div id="logo-placeholder" class="flex flex-col items-center justify-center text-center p-2">
                  <svg class="w-8 h-8 text-slate-500 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                  </svg>
                  <p class="text-xs text-slate-500">No logo</p>
                </div>
              {% endif %}
            </div>

            <div class="flex-1 space-y-2">
              <div class="settings-field">
                {% render_field form.logo id="logo-upload" %}
              </div>
              <p class="text-xs text-slate-500">PNG, JPG or WebP. Recommended 200×200px or larger.</p>
              {% if profile and profile.logo %}
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" name="clear_logo" id="clear-logo"
                       class="w-4 h-4 accent-red-500 rounded" />
                <span class="text-xs text-red-400 font-medium">Remove current logo</span>
              </label>
              {% endif %}
            </div>
          </div>
        </div>

        <div class="settings-field">
          <label>Business Name *</label>
          {% render_field form.name %}
          {% if form.name.errors %}
          <p class="text-red-400 text-xs mt-1">{{ form.name.errors|join:", " }}</p>
          {% endif %}
        </div>

        <div class="settings-field">
          <label>Tagline <span class="text-slate-500 normal-case font-normal">(optional)</span></label>
          {% render_field form.tagline %}
        </div>

      </div>
    </div>

    <!-- ── CONTACT DETAILS ──────────────────────────────────────────────── -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
      <div class="px-5 py-4 border-b border-surface-700 bg-surface-700/30">
        <h2 class="text-sm font-heading font-semibold text-white">Contact Details</h2>
      </div>
      <div class="p-5 space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="settings-field">
            <label>Phone</label>
            {% render_field form.phone %}
          </div>
          <div class="settings-field">
            <label>Email</label>
            {% render_field form.email %}
          </div>
        </div>
        <div class="settings-field">
          <label>Website</label>
          {% render_field form.website %}
        </div>
        <div class="settings-field">
          <label>Tax ID / TIN / RC Number</label>
          {% render_field form.tax_id %}
        </div>
      </div>
    </div>

    <!-- ── ADDRESS ──────────────────────────────────────────────────────── -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
      <div class="px-5 py-4 border-b border-surface-700 bg-surface-700/30">
        <h2 class="text-sm font-heading font-semibold text-white">Business Address</h2>
      </div>
      <div class="p-5 space-y-4">
        <div class="settings-field">
          <label>Address Line 1</label>
          {% render_field form.address_line1 %}
        </div>
        <div class="settings-field">
          <label>Address Line 2 <span class="text-slate-500 normal-case font-normal">(optional)</span></label>
          {% render_field form.address_line2 %}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="settings-field">
            <label>City</label>
            {% render_field form.city %}
          </div>
          <div class="settings-field">
            <label>State</label>
            {% render_field form.state %}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="settings-field">
            <label>Country</label>
            {% render_field form.country %}
          </div>
          <div class="settings-field">
            <label>Postal Code</label>
            {% render_field form.postal_code %}
          </div>
        </div>
      </div>
    </div>

    <!-- ── BANKING DETAILS ──────────────────────────────────────────────── -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
      <div class="px-5 py-4 border-b border-surface-700 bg-surface-700/30">
        <h2 class="text-sm font-heading font-semibold text-white">Banking Details</h2>
        <p class="text-xs text-slate-400 mt-0.5">Shown on invoice PDFs to guide client payment</p>
      </div>
      <div class="p-5 space-y-4">
        <div class="settings-field">
          <label>Bank Name</label>
          {% render_field form.bank_name %}
        </div>
        <div class="settings-field">
          <label>Account Name</label>
          {% render_field form.account_name %}
        </div>
        <div class="settings-field">
          <label>Account Number</label>
          {% render_field form.account_number %}
        </div>
      </div>
    </div>

    <!-- ── PDF NOTES ────────────────────────────────────────────────────── -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
      <div class="px-5 py-4 border-b border-surface-700 bg-surface-700/30">
        <h2 class="text-sm font-heading font-semibold text-white">PDF Footer Notes</h2>
        <p class="text-xs text-slate-400 mt-0.5">Printed at the bottom of every PDF</p>
      </div>
      <div class="p-5 space-y-4">
        <div class="settings-field">
          <label>Invoice Footer Note</label>
          {% render_field form.invoice_footer_note %}
        </div>
        <div class="settings-field">
          <label>Receipt Footer Note</label>
          {% render_field form.receipt_footer_note %}
        </div>
      </div>
    </div>

    <!-- ── SETUP STATUS ─────────────────────────────────────────────────── -->
    {% if not profile %}
    <div class="bg-amber-900/30 border border-amber-700/50 rounded-2xl p-4 flex items-start gap-3">
      <svg class="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <div>
        <p class="text-sm font-semibold text-amber-300">Business profile not set up</p>
        <p class="text-xs text-amber-400/80 mt-0.5">
          PDFs will show placeholder business information until you save your profile.
        </p>
      </div>
    </div>
    {% endif %}

    <!-- Save Button -->
    <div class="pb-6">
      <button type="submit"
              class="w-full py-4 rounded-2xl bg-brand-500 hover:bg-brand-600 text-white font-heading font-bold text-base shadow-xl shadow-brand-500/30 transition-all active:scale-[0.98]">
        Save Settings
      </button>
    </div>

  </div>
</form>
{% endblock %}

{% block extra_scripts %}
<script>
  // Live logo preview on file selection
  const logoUpload = document.getElementById('logo-upload');
  const logoPreview = document.getElementById('logo-preview');
  const logoPlaceholder = document.getElementById('logo-placeholder');
  const logoContainer = document.getElementById('logo-preview-container');

  if (logoUpload) {
    logoUpload.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function(evt) {
        // Remove placeholder if exists
        if (logoPlaceholder) logoPlaceholder.style.display = 'none';

        // Update or create img tag
        let img = document.getElementById('logo-preview');
        if (!img) {
          img = document.createElement('img');
          img.id = 'logo-preview';
          img.className = 'w-full h-full object-contain';
          logoContainer.appendChild(img);
        }
        img.src = evt.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  // If "Remove logo" is checked, show greyed out container
  const clearLogoCheckbox = document.getElementById('clear-logo');
  if (clearLogoCheckbox) {
    clearLogoCheckbox.addEventListener('change', function() {
      const img = document.getElementById('logo-preview');
      if (img) img.style.opacity = this.checked ? '0.2' : '1';
    });
  }
</script>
{% endblock %}
```

---

## 5. Handle `enctype="multipart/form-data"` on the Settings Form

The form includes a file upload (logo). Ensure:
- `<form method="post" enctype="multipart/form-data">` — already in the template above
- The view uses `request.FILES` — already handled in the view above
- `MEDIA_ROOT` and `MEDIA_URL` are configured in `settings.py` — confirmed in Wave 1
- Media files are served in development via the `urlpatterns` `+ static(...)` in `invoice_system/urls.py` — confirmed in Wave 1

---

## 6. Setup Completion Indicator on Dashboard

On the `core/templates/core/dashboard.html`, add a setup banner at the very top if no
`BusinessProfile` exists yet:

```html
{% if not business_profile %}
<div class="bg-amber-900/30 border border-amber-700/50 rounded-2xl p-4 flex items-center justify-between gap-4">
  <div class="flex items-start gap-3">
    <svg class="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
    </svg>
    <div>
      <p class="text-sm font-semibold text-amber-300">Set up your business profile</p>
      <p class="text-xs text-amber-400/80 mt-0.5">Your business info will appear on all PDFs</p>
    </div>
  </div>
  <a href="{% url 'core:settings' %}"
     class="flex-shrink-0 px-3 py-2 rounded-xl bg-amber-700/50 hover:bg-amber-700 text-amber-300 text-xs font-semibold transition-colors">
    Set Up →
  </a>
</div>
{% endif %}
```

Pass `business_profile` to the dashboard context in `views.py`:
```python
'business_profile': BusinessProfile.get_profile(),
```

---

## 7. Context Processor (Optional but Recommended)

To make `BusinessProfile` available in ALL templates (for the header/nav), create a
context processor:

Create `core/context_processors.py`:

```python
from .models import BusinessProfile


def business_profile(request):
    """Make business profile available in all templates."""
    return {
        'business_profile': BusinessProfile.get_profile(),
    }
```

Add to `TEMPLATES[0]['OPTIONS']['context_processors']` in `settings.py`:

```python
'core.context_processors.business_profile',
```

After doing this, `{{ business_profile }}` is available in ALL templates including
`base.html` — so the sidebar can show the business name, and the dashboard banner
doesn't need it explicitly passed.

---

## Acceptance Criteria

Before marking Wave 6 complete, verify ALL of the following:

- [ ] `http://127.0.0.1:8000/settings/` loads the settings page
- [ ] Settings page shows all sections: Identity, Contact, Address, Banking, PDF Notes
- [ ] Saving the form with a business name updates the profile
- [ ] Uploading a logo shows a live preview immediately on the page (no page reload)
- [ ] After saving with a logo, the logo appears in the preview on page reload
- [ ] "Remove current logo" checkbox removes the logo when form is saved
- [ ] Settings link in both sidebar and bottom nav navigates to settings page
- [ ] Settings nav item highlights as active on the settings page
- [ ] Dashboard shows setup banner if no business profile exists
- [ ] Dashboard setup banner disappears after business profile is saved
- [ ] `BusinessProfile` context processor makes profile available in `base.html`
- [ ] Only one `BusinessProfile` can exist (verified via Django shell)
- [ ] PDF generated after settings save shows updated business info

---

## Do NOT do in this wave
- Do not build email sending (Wave 7)
- Do not add system-level overdue CRON or scheduled tasks (Wave 8 scope)
