from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('invoices/',                   views.invoice_list,   name='invoice_list'),
    path('invoices/new/',               views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/',          views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/',     views.invoice_edit,   name='invoice_edit'),
    path('invoices/<int:pk>/delete/',      views.invoice_delete,   name='invoice_delete'),
    path('invoices/<int:pk>/cancel/',      views.invoice_cancel,   name='invoice_cancel'),
    path('invoices/<int:pk>/sent/',        views.mark_as_sent,     name='mark_as_sent'),
    path('invoices/<int:pk>/pay/',         views.mark_as_paid,     name='mark_as_paid'),
    path('invoices/<int:pk>/receipt/',     views.receipt_detail,   name='receipt_detail'),
    path('invoices/<int:pk>/pdf/',         views.invoice_pdf,      name='invoice_pdf'),
    path('invoices/<int:pk>/receipt/pdf/', views.receipt_pdf,      name='receipt_pdf'),

    path('settings/',                    views.settings_view,  name='settings'),

    path('clients/',                    views.client_list,    name='client_list'),
    path('clients/new/',                views.client_create,  name='client_create'),
    path('clients/<int:pk>/',           views.client_detail,  name='client_detail'),
    path('clients/<int:pk>/edit/',      views.client_edit,    name='client_edit'),
]
