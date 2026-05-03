from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import FeePayment

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ['student', 'payment_type', 'amount', 'status', 'date_requested', 'approved_by']
    list_filter = ['status', 'payment_type', 'session']
    list_editable = ['status']
    search_fields = ['student__reg_number', 'receipt_number']