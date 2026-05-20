from django.urls import path
from . import views

app_name = "admissions"

urlpatterns = [
    # Public
    path("apply/",                          views.apply,                 name="apply"),
    path("submitted/<int:pk>/",             views.submitted,             name="submitted"),
    path("check-status/",                   views.check_status,          name="check_status"),

    # Student portal
    path("invoice/",                        views.generate_invoice,      name="generate_invoice"),
    path("invoice/pdf/",                    views.invoice_pdf,           name="invoice_pdf"),

    # Registrar
    path("manage/",                         views.registrar_list,        name="registrar_list"),
    path("manage/<int:pk>/",               views.registrar_detail,      name="registrar_detail"),
    path("manage/<int:pk>/confirm-fee/",   views.confirm_app_fee,       name="confirm_app_fee"),
    path("manage/<int:pk>/admit/",         views.admit,                 name="admit"),
    path("manage/<int:pk>/reject/",        views.reject,                name="reject"),
    path("manage/<int:pk>/letter/",        views.admission_letter,      name="admission_letter"),
    path("school-fees/",                    views.registrar_school_fees, name="registrar_school_fees"),
    path("school-fees/<int:pk>/approve/",  views.approve_school_fee,    name="approve_school_fee"),
    path("school-fees/<int:pk>/reject/",   views.reject_school_fee,     name="reject_school_fee"),
]
