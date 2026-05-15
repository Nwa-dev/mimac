# WAVE 8 — Polish & Mobile UX

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1–7 are complete: scaffold, models, CRUD, PDFs, payment flow, settings, and email
are all working. This is Wave 8 — the final wave. Build ONLY what is specified here.

This wave is about elevating the product from functional to polished. Every rough edge,
every missing empty state, every broken active nav item, every jarring transition gets
fixed here. The goal is a system that feels like a real native app.

---

## Objectives
- Fix all active state detection across the bottom nav and sidebar
- Add proper empty states to every list page
- Add loading/submitting states to all form buttons
- Implement toast auto-dismiss and slide-in animations
- Add overdue detection that runs on every page load
- Add a scrollbar-hide utility for horizontal tabs
- Handle mobile safe-area-inset for bottom nav
- Add smooth page entry animations
- Add a confirmation modal for destructive actions (delete)
- Add a "copy invoice number" convenience button
- Polish invoice detail page layout
- Add client invoice count badge on client list
- Add a "this month" revenue metric to the dashboard
- Final QA across all views at 390px and 1280px viewports

---

## 1. CSS Utilities (add to `base.html` `<style>` block)

Add these utilities inside the existing `<style>` tag in `base.html`:

```css
/* Scrollbar hide — for horizontal filter tabs */
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }

/* Safe area for iOS bottom nav */
.safe-area-bottom { padding-bottom: env(safe-area-inset-bottom, 0px); }

/* Toast slide-in animation */
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}
.toast-notification { animation: slideInRight 0.3s ease forwards; }

/* Toast slide-out */
@keyframes slideOutRight {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(20px); }
}
.toast-exit { animation: slideOutRight 0.3s ease forwards; }

/* Page content fade-in on load */
@keyframes pageIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
main { animation: pageIn 0.25s ease forwards; }

/* Bounce-once for receipt success icon */
@keyframes bounceIn {
  0%   { transform: scale(0.3); opacity: 0; }
  50%  { transform: scale(1.1); }
  70%  { transform: scale(0.95); }
  100% { transform: scale(1); opacity: 1; }
}
.animate-bounce-in { animation: bounceIn 0.5s ease forwards; }

/* Pulse ring for success icon */
@keyframes pulseRing {
  0%   { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  70%  { box-shadow: 0 0 0 16px rgba(16,185,129,0); }
  100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); }
}
.pulse-ring { animation: pulseRing 2s ease infinite; }

/* Skeleton loading shimmer */
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

/* Button loading spinner */
@keyframes spin { to { transform: rotate(360deg); } }
.btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
```

---

## 2. Bottom Nav — Safe Area & Active State Fixes (`base.html`)

Update the mobile bottom nav `<nav>` tag:

```html
<nav class="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface-800 border-t border-surface-700 px-2 pt-2 pb-2 safe-area-bottom">
```

Ensure ALL five bottom nav items have correct active state detection.
Replace placeholder `{% if ... %}active{% endif %}` blocks with these:

```html
<!-- Home / Dashboard -->
{% if request.resolver_match.url_name == 'dashboard' %}active bg-surface-700{% endif %}

<!-- Invoices (active on invoice_list, invoice_detail, invoice_create, invoice_edit) -->
{% if request.resolver_match.url_name in 'invoice_list,invoice_detail,invoice_create,invoice_edit,mark_as_paid,receipt_detail' %}active bg-surface-700{% endif %}

<!-- New Invoice FAB — always visible, no active state needed -->

<!-- Clients (active on client_list, client_detail, client_create, client_edit) -->
{% if request.resolver_match.url_name in 'client_list,client_detail,client_create,client_edit' %}active bg-surface-700{% endif %}

<!-- Settings -->
{% if request.resolver_match.url_name == 'settings' %}active bg-surface-700{% endif %}
```

**Django template note:** The `in` operator on a string checks substring, not list membership.
Use individual comparisons for correctness:

```html
{% if request.resolver_match.url_name == 'invoice_list' or request.resolver_match.url_name == 'invoice_detail' or request.resolver_match.url_name == 'invoice_create' or request.resolver_match.url_name == 'invoice_edit' %}active bg-surface-700{% endif %}
```

Or create a custom template tag (see section 9).

---

## 3. Toast Notification Improvements (`base.html` JS)

Replace the existing toast auto-dismiss script with this improved version:

```javascript
// Toast notifications: auto-dismiss with animation
document.querySelectorAll('.toast-notification').forEach((el, i) => {
  // Stagger multiple toasts
  el.style.animationDelay = `${i * 100}ms`;

  const dismiss = () => {
    el.classList.add('toast-exit');
    setTimeout(() => el.remove(), 300);
  };

  // Auto dismiss after 4 seconds
  const timer = setTimeout(dismiss, 4000);

  // Allow manual dismiss
  const closeBtn = el.querySelector('[data-dismiss-toast]');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      clearTimeout(timer);
      dismiss();
    });
  }

  // Pause auto-dismiss on hover
  el.addEventListener('mouseenter', () => clearTimeout(timer));
  el.addEventListener('mouseleave', () => setTimeout(dismiss, 2000));
});
```

Update toast close button to use `data-dismiss-toast` attribute:
```html
<button data-dismiss-toast class="text-white/70 hover:text-white mt-0.5">
```

---

## 4. Button Loading States

Add this JavaScript to every template that has a form submit button.
Place in `{% block extra_scripts %}`.

**Reusable approach — add to `base.html`:**

```javascript
// Submit button loading state
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function(e) {
    const submitBtn = form.querySelector('[type="submit"]');
    if (!submitBtn) return;

    // Store original content
    const originalContent = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <span class="btn-spinner"></span>
      <span>${submitBtn.dataset.loadingText || 'Processing...'}</span>
    `;
    submitBtn.style.display = 'flex';
    submitBtn.style.alignItems = 'center';
    submitBtn.style.justifyContent = 'center';
    submitBtn.style.gap = '8px';

    // Re-enable after 10s as failsafe
    setTimeout(() => {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalContent;
    }, 10000);
  });
});
```

Add `data-loading-text` attributes to key buttons:
- Invoice form submit: `data-loading-text="Saving..."`
- Mark as Paid: `data-loading-text="Recording Payment..."`
- Send to Client: `data-loading-text="Sending..."`
- Settings save: `data-loading-text="Saving..."`

---

## 5. Overdue Detection Middleware

Instead of checking for overdue invoices only on the dashboard, run the check on every
request automatically using a lightweight middleware.

Create `core/middleware.py`:

```python
from django.utils import timezone


class OverdueCheckMiddleware:
    """
    Marks overdue invoices on every GET request.
    Runs the check at most once per 10 minutes to avoid redundant queries.
    Uses Django's session to throttle.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'GET' and not request.path.startswith('/admin/'):
            self._check_overdue(request)
        return self.get_response(request)

    def _check_overdue(self, request):
        last_check_key = '_overdue_checked_at'
        last_check = request.session.get(last_check_key)
        now_ts = timezone.now().timestamp()

        # Check at most once every 10 minutes
        if last_check and (now_ts - last_check) < 600:
            return

        try:
            from core.models import Invoice
            updated = Invoice.objects.filter(
                status__in=['sent', 'draft'],
                due_date__lt=timezone.now().date()
            ).update(status='overdue')

            request.session[last_check_key] = now_ts

        except Exception:
            pass  # Never let overdue check crash a page
```

Register in `settings.py` — add to `MIDDLEWARE` list after `SessionMiddleware`:

```python
'core.middleware.OverdueCheckMiddleware',
```

---

## 6. Custom Template Tag — `url_name_in`

Create `core/templatetags/core_tags.py`:

```python
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def active_if(context, *url_names):
    """
    Returns 'active' if the current URL name matches any of the given names.

    Usage:
      {% active_if 'invoice_list' 'invoice_detail' 'invoice_create' %}
    """
    request = context.get('request')
    if not request:
        return ''
    current = request.resolver_match.url_name if request.resolver_match else ''
    return 'active' if current in url_names else ''


@register.filter
def currency(value):
    """Format a number as Nigerian Naira."""
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₦0.00"


@register.filter
def percentage(value):
    """Format a number as a percentage."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0%"
```

Create `core/templatetags/__init__.py` (empty file).

**Usage in templates:**
```html
{% load core_tags %}
<a class="nav-item {% active_if 'invoice_list' 'invoice_detail' 'invoice_create' %}">
```

---

## 7. Dashboard — "This Month" Revenue Card

Add a fifth stat to the dashboard: revenue received this month.

In `dashboard` view, add to context:

```python
from django.utils import timezone

now = timezone.now()
this_month_paid = Invoice.objects.filter(
    status='paid',
    paid_at__year=now.year,
    paid_at__month=now.month,
).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

context['this_month_paid'] = this_month_paid
context['current_month_name'] = now.strftime('%B')
```

Update the dashboard stats grid from 2×2 to 2×2 + 1 wide card at bottom:

```html
<!-- Stats Grid — 2 columns on mobile, 4 on desktop -->
<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
  <!-- existing 4 cards -->
</div>

<!-- This Month Card — full width -->
<div class="bg-gradient-to-r from-brand-700/30 to-brand-600/20 rounded-2xl p-4 border border-brand-700/30 flex items-center justify-between">
  <div>
    <p class="text-xs text-brand-300 font-semibold uppercase tracking-wider">{{ current_month_name }} Revenue</p>
    <p class="text-2xl font-heading font-extrabold text-white mt-1">₦{{ this_month_paid|floatformat:0 }}</p>
  </div>
  <div class="w-12 h-12 rounded-2xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
    <svg class="w-6 h-6 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
    </svg>
  </div>
</div>
```

---

## 8. Invoice Detail — Polish Pass

Rebuild `core/templates/core/invoice_detail.html` with a fully polished layout:

### Sections (top to bottom):

**1. Sticky header bar (mobile)**
```html
<div class="flex items-center justify-between mb-5">
  <div class="flex items-center gap-3">
    <a href="{% url 'core:invoice_list' %}" class="p-2 rounded-xl bg-surface-800 border border-surface-700">
      <!-- back arrow -->
    </a>
    <div>
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-heading font-bold text-white">{{ invoice.invoice_number }}</h1>
        <!-- Copy button -->
        <button onclick="navigator.clipboard.writeText('{{ invoice.invoice_number }}').then(() => showCopied(this))"
                class="p-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 transition-colors group">
          <svg class="w-3.5 h-3.5 text-slate-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
        </button>
      </div>
      <span class="inline-flex mt-1 items-center px-2 py-0.5 rounded-lg text-xs font-semibold {{ invoice.status_color }}">
        {{ invoice.get_status_display }}
      </span>
    </div>
  </div>
  <div class="text-right">
    <p class="text-xs text-slate-400">Total</p>
    <p class="text-xl font-heading font-extrabold text-white">₦{{ invoice.total_amount|floatformat:2 }}</p>
  </div>
</div>
```

**Copy button JS (add to extra_scripts):**
```javascript
function showCopied(btn) {
  const original = btn.innerHTML;
  btn.innerHTML = '<svg class="w-3.5 h-3.5 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>';
  setTimeout(() => btn.innerHTML = original, 1500);
}
```

**2. Meta info card**

Two-column grid: From / Bill To / Dates.

**3. Line items card**

Clean table with description, qty × price = total per row.
A subtle divider between items. Totals right-aligned at bottom.

**4. Payment confirmed block** (for paid invoices)

Green card: paid date, method, reference, amount received.

**5. Action buttons**

Conditional based on status. Arrange vertically on mobile, horizontally on desktop.

---

## 9. Client List — Invoice Count Badge

In `client_list` view, annotate queryset with invoice count:

```python
from django.db.models import Count, Sum

clients = Client.objects.annotate(
    invoice_count=Count('invoices'),
    total_invoiced_amt=Sum('invoices__total_amount'),
).order_by('name')
```

Update client cards in `client_list.html`:

```html
<div class="flex items-center justify-between gap-4">
  <div class="flex-1 min-w-0">
    <p class="text-sm font-bold text-white truncate">{{ client }}</p>
    <p class="text-xs text-slate-400 mt-0.5">{{ client.email|default:"No email" }}</p>
  </div>
  <div class="text-right flex-shrink-0">
    <p class="text-xs text-slate-400">{{ client.invoice_count }} invoice{{ client.invoice_count|pluralize }}</p>
    {% if client.total_invoiced_amt %}
    <p class="text-sm font-semibold text-white">₦{{ client.total_invoiced_amt|floatformat:0 }}</p>
    {% endif %}
  </div>
</div>
```

---

## 10. Delete Confirmation — Inline Modal

Replace the separate delete confirmation page with an inline modal overlay.
This prevents the jarring navigation away just to confirm deletion.

Add this modal to `invoice_detail.html`:

```html
<!-- Delete Confirmation Modal -->
<div id="delete-modal" class="hidden fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" onclick="closeDeleteModal()"></div>

  <!-- Modal Card -->
  <div class="relative bg-surface-800 border border-surface-700 rounded-3xl p-6 w-full max-w-sm z-10 shadow-2xl">
    <div class="flex items-start gap-4 mb-5">
      <div class="w-11 h-11 rounded-2xl bg-red-900/50 border border-red-800 flex items-center justify-center flex-shrink-0">
        <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
      </div>
      <div>
        <h3 class="text-base font-heading font-bold text-white">Delete Invoice?</h3>
        <p class="text-sm text-slate-400 mt-1">
          This will permanently delete <strong class="text-white">{{ invoice.invoice_number }}</strong>.
          This action cannot be undone.
        </p>
      </div>
    </div>
    <div class="flex gap-3">
      <button onclick="closeDeleteModal()"
              class="flex-1 py-3 rounded-xl bg-surface-700 hover:bg-surface-600 text-slate-300 text-sm font-semibold transition-colors">
        Keep It
      </button>
      <form method="post" action="{% url 'core:invoice_delete' invoice.pk %}" class="flex-1">
        {% csrf_token %}
        <button type="submit"
                class="w-full py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-semibold transition-colors">
          Delete
        </button>
      </form>
    </div>
  </div>
</div>
```

Add delete modal trigger JS:

```javascript
function openDeleteModal() {
  document.getElementById('delete-modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}
function closeDeleteModal() {
  document.getElementById('delete-modal').classList.add('hidden');
  document.body.style.overflow = '';
}
```

Replace the delete link to call `openDeleteModal()` instead of navigating away.

---

## 11. Receipt Detail — Animate Success Icon

Update the success icon in `receipt_detail.html` to use the new animation classes:

```html
<div class="w-20 h-20 rounded-full bg-brand-500/20 border-2 border-brand-500 flex items-center justify-center mx-auto mb-5 animate-bounce-in pulse-ring">
  <svg class="w-10 h-10 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
  </svg>
</div>
```

---

## 12. 404 & 500 Error Pages

Create branded error pages:

**`core/templates/404.html`:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>404 — Page Not Found</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@700;800&family=Inter&display=swap" rel="stylesheet"/>
  <style>body { font-family: 'Inter', sans-serif; } h1, h2 { font-family: 'Sora', sans-serif; }</style>
</head>
<body class="bg-slate-900 text-white flex items-center justify-center min-h-screen p-6">
  <div class="text-center">
    <p class="text-8xl font-extrabold text-emerald-500 opacity-30 select-none">404</p>
    <h1 class="text-2xl font-bold text-white mt-2">Page Not Found</h1>
    <p class="text-slate-400 mt-2 text-sm">The page you're looking for doesn't exist or has been moved.</p>
    <a href="/" class="inline-flex items-center gap-2 mt-6 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl font-semibold text-sm transition-colors">
      Back to Dashboard
    </a>
  </div>
</body>
</html>
```

**`core/templates/500.html`:** — same structure but with "500" and "Server Error" text.

Register in `invoice_system/urls.py`:
```python
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'
```

Add to `core/views.py`:
```python
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)
```

Set `DEBUG = False` in settings to see custom error pages (use a test endpoint).

---

## 13. Favicon

Add a simple SVG favicon to `base.html` `<head>`:

```html
<!-- SVG Favicon -->
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%230f172a'/><rect x='20' y='15' width='60' height='70' rx='6' fill='%2310b981'/><rect x='30' y='35' width='40' height='4' rx='2' fill='white'/><rect x='30' y='48' width='40' height='4' rx='2' fill='white'/><rect x='30' y='61' width='25' height='4' rx='2' fill='white'/></svg>" />
```

---

## 14. Final QA Checklist

Run through every view manually at **390px viewport** and **1280px viewport** and verify:

### Dashboard
- [ ] Stats cards display correctly without overflow
- [ ] "This month" card shows current month name
- [ ] Setup banner shows only when no business profile
- [ ] Recent invoices list is readable at 390px
- [ ] New Invoice button visible and tappable

### Invoice List
- [ ] Status filter tabs scroll horizontally on mobile without showing scrollbar
- [ ] All filter tabs show correct counts
- [ ] Invoice cards show full info without overflow
- [ ] "No invoices found" empty state shows when appropriate

### Invoice Create/Edit
- [ ] Line items add/remove work
- [ ] Totals update live
- [ ] Date pickers work on mobile (native date input)
- [ ] Submit button shows spinner while submitting

### Invoice Detail
- [ ] Copy invoice number button works
- [ ] Status badge correct color for all 5 states
- [ ] Action buttons correct for all 5 states
- [ ] Delete modal opens and closes correctly
- [ ] View PDF opens in new tab
- [ ] Download PDF triggers file download

### Payment Flow
- [ ] Mark as Paid form pre-fills correctly
- [ ] Confirm Payment shows loading state
- [ ] Receipt page shows green hero with bounce animation
- [ ] Download Receipt PDF works
- [ ] Resend Receipt button visible (if client has email)

### Client List & Detail
- [ ] Search filters correctly
- [ ] Invoice count badge shows on client cards
- [ ] Client detail shows invoice list
- [ ] Edit client form pre-fills

### Settings
- [ ] Logo upload shows live preview
- [ ] Remove logo checkbox works
- [ ] Save shows loading state
- [ ] All fields save and persist

### Navigation
- [ ] Active state correct on all nav items (mobile bottom nav)
- [ ] Active state correct on all sidebar links (desktop)
- [ ] FAB (New Invoice) navigates to invoice create
- [ ] Settings link works from both nav locations

### General
- [ ] Toast messages appear and auto-dismiss
- [ ] Close button on toast works
- [ ] 404 page shows for invalid URLs
- [ ] No console errors on any page
- [ ] `python manage.py check` returns no issues

---

## Acceptance Criteria

Before marking Wave 8 complete, verify ALL of the following:

- [ ] All nav active states work correctly across both sidebar and bottom nav on all pages
- [ ] Horizontal filter tabs hide scrollbar on mobile
- [ ] Bottom nav has proper iOS safe area padding
- [ ] All form submit buttons show spinner while submitting
- [ ] Toast notifications slide in, pause on hover, and slide out
- [ ] Overdue middleware marks invoices automatically without breaking any page
- [ ] Dashboard shows "This Month" revenue with current month name
- [ ] Client cards show invoice count
- [ ] Invoice detail delete uses inline modal (no separate page)
- [ ] Receipt success icon has bounce animation
- [ ] Copy invoice number button shows checkmark confirmation
- [ ] 404 page is branded and links back to dashboard
- [ ] SVG favicon visible in browser tab
- [ ] Zero Django system check errors (`python manage.py check`)
- [ ] All pages usable on 390px mobile viewport with no horizontal overflow
- [ ] All pages usable on 1280px desktop with sidebar visible

---

## Do NOT do in this wave
- Do not add user authentication / login (out of scope)
- Do not add multi-currency support (out of scope)
- Do not add recurring invoices (out of scope)
- Do not add Celery or background task queue for scheduled jobs
