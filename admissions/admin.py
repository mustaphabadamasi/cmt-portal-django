from django.contrib import admin
from .models import Application, OLevelResult, OLevelSubject, SchoolFeeInvoice

class SubjectInline(admin.TabularInline):
    model = OLevelSubject
    extra = 0

class OLevelInline(admin.StackedInline):
    model = OLevelResult
    extra = 0

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ("application_number","get_full_name","programme","status","app_fee_confirmed","created_at")
    list_filter   = ("status","programme","app_fee_confirmed")
    search_fields = ("application_number","first_name","last_name","email","phone")
    inlines       = [OLevelInline]

@admin.register(SchoolFeeInvoice)
class SchoolFeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number","application","amount","status","created_at")
    list_filter  = ("status",)
