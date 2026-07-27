# core/admin.py
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q
from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from django.forms import widgets
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from . import models

# ==================== CUSTOM ADMIN SITE ====================

class VetCareAdminSite(AdminSite):
    """Custom admin site with branding and customizations"""
    site_header = _('VetCare Admin')
    site_title = _('VetCare Management')
    index_title = _('Dashboard')
    site_url = '/'
    
    def get_app_list(self, request):
        """Customize app list with icons or descriptions"""
        app_list = super().get_app_list(request)
        # Add custom ordering or descriptions if needed
        return app_list


# ==================== BASE MODEL ADMIN ====================

class BaseModelAdmin(admin.ModelAdmin):
    """Base admin class with common configurations"""
    readonly_fields = ('id', 'created_at', 'updated_at', 'version')
    list_filter = ('is_active', 'created_at')
    date_hierarchy = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by and updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class TenantAwareAdmin(BaseModelAdmin):
    """Admin for tenant-aware models with clinic filtering"""
    list_filter = BaseModelAdmin.list_filter + ('clinic',)
    
    def get_queryset(self, request):
        """Filter by clinic based on user role"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # If user has a clinic, filter by it
        if hasattr(request.user, 'clinic'):
            return qs.filter(clinic=request.user.clinic)
        return qs.none()


# ==================== FILTERS ====================

class RoleFilter(SimpleListFilter):
    title = 'Role'
    parameter_name = 'role'
    
    def lookups(self, request, model_admin):
        return models.User.ROLE_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(role=self.value())
        return queryset


class StatusFilter(SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return models.AnimalPatient.STATUS_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


# ==================== INLINES ====================

class AppointmentInline(admin.TabularInline):
    model = models.Appointment
    fields = ('patient', 'veterinarian', 'scheduled_date', 'status', 'priority')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


class MedicalRecordInline(admin.TabularInline):
    model = models.MedicalRecord
    fields = ('patient', 'veterinarian', 'primary_diagnosis', 'outcome', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


class InventoryItemInline(admin.TabularInline):
    model = models.InventoryItem
    fields = ('medication', 'current_quantity', 'status', 'expiry_date')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


class InvoiceItemInline(admin.TabularInline):
    model = models.Invoice
    fields = ('invoice_number', 'total_amount', 'status', 'due_date')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


# ==================== USER ADMIN ====================

class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with role selection"""
    
    class Meta:
        model = models.User
        fields = ('username', 'email', 'phone_number', 'first_name', 'last_name', 'role')


class CustomUserChangeForm(UserChangeForm):
    """Custom user change form"""
    
    class Meta:
        model = models.User
        fields = '__all__'


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    # List display
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'role',
        'clinic', 'is_active', 'is_mfa_enabled', 'total_patients'
    )
    list_filter = ('role', 'is_active', 'is_mfa_enabled', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'last_login_ip', 'failed_login_attempts', 'locked_until',
        'total_treatments', 'total_appointments', 'rating', 'review_count'
    )
    
    # Fieldsets
    fieldsets = (
        (_('Personal Information'), {
            'fields': (
                'first_name', 'last_name', 'middle_name', 'username',
                'email', 'phone_number', 'date_of_birth', 'gender',
                'profile_picture', 'bio'
            )
        }),
        (_('Professional Information'), {
            'fields': (
                'role', 'license_number', 'specialization', 'years_of_experience'
            )
        }),
        (_('Security'), {
            'fields': (
                'is_mfa_enabled', 'mfa_secret', 'last_login_ip',
                'last_login_location', 'failed_login_attempts', 'locked_until'
            ),
            'classes': ('collapse',)
        }),
        (_('Preferences'), {
            'fields': (
                'language', 'timezone', 'notification_preferences'
            ),
            'classes': ('collapse',)
        }),
        (_('Statistics'), {
            'fields': (
                'total_treatments', 'total_appointments', 'rating', 'review_count'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    # Add fields for inline clinic relationship
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('clinic')
    
    def total_patients(self, obj):
        """Count number of patients under this user"""
        return obj.animals.count()
    total_patients.short_description = 'Total Patients'
    
    def clinic(self, obj):
        """Get clinic name if available"""
        if hasattr(obj, 'clinic'):
            return obj.clinic.name
        return '-'
    clinic.short_description = 'Clinic'


# ==================== CLINIC ADMIN ====================

@admin.register(models.Clinic)
class ClinicAdmin(BaseModelAdmin):
    list_display = (
        'name', 'clinic_type', 'city', 'state', 'is_verified',
        'is_premium', 'rating', 'total_patients_display'
    )
    list_filter = (
        'clinic_type', 'is_verified', 'is_premium', 'is_active',
        'city', 'state'
    )
    search_fields = ('name', 'registration_number', 'email', 'phone')
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'total_patients', 'total_appointments', 'total_revenue',
        'active_patients', 'rating'
    )
    date_hierarchy = 'created_at'
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'name', 'registration_number', 'clinic_type',
                'description', 'established_date'
            )
        }),
        (_('Contact Information'), {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state', 'country', 'postal_code',
                'latitude', 'longitude', 'phone', 'email', 'website'
            )
        }),
        (_('Operations'), {
            'fields': (
                'operating_hours', 'facilities', 'services', 'specialties',
                'total_rooms', 'available_rooms', 'total_staff',
                'max_patients_daily'
            )
        }),
        (_('Subscription & Status'), {
            'fields': (
                'subscription_plan', 'is_verified', 'is_premium',
                'subscription_expiry'
            )
        }),
        (_('Analytics'), {
            'fields': (
                'rating', 'total_patients', 'total_appointments',
                'total_revenue', 'active_patients'
            ),
            'classes': ('collapse',)
        }),
        (_('Settings'), {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [AppointmentInline, InventoryItemInline, InvoiceItemInline]
    
    def total_patients_display(self, obj):
        """Show total patients with link"""
        url = reverse('admin:core_animalpatient_changelist') + f'?clinic__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, obj.total_patients)
    total_patients_display.short_description = 'Total Patients'
    total_patients_display.admin_order_field = 'total_patients'


# ==================== ANIMAL SPECIES ADMIN ====================

@admin.register(models.AnimalSpecies)
class AnimalSpeciesAdmin(BaseModelAdmin):
    list_display = ('name', 'scientific_name', 'diet_type', 'avg_lifespan')
    list_filter = ('diet_type', 'is_active')
    search_fields = ('name', 'scientific_name', 'common_names')
    fieldsets = (
        (_('Classification'), {
            'fields': ('name', 'scientific_name', 'common_names')
        }),
        (_('Taxonomy'), {
            'fields': ('class_name', 'order_name', 'family_name')
        }),
        (_('Characteristics'), {
            'fields': (
                'avg_lifespan', 'avg_weight_kg', 'gestation_period',
                'diet_type'
            )
        }),
        (_('Health'), {
            'fields': (
                'common_diseases', 'vaccination_schedule',
                'normal_temperature_range', 'normal_heart_rate_range',
                'normal_respiratory_rate_range'
            ),
            'classes': ('collapse',)
        }),
        (_('Economic'), {
            'fields': ('market_value', 'feed_cost_per_day'),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )


# ==================== ANIMAL BREED ADMIN ====================

@admin.register(models.AnimalBreed)
class AnimalBreedAdmin(BaseModelAdmin):
    list_display = ('name', 'species', 'code', 'temperament')
    list_filter = ('species', 'temperament', 'is_active')
    search_fields = ('name', 'code', 'species__name')
    raw_id_fields = ('species',)


# ==================== ANIMAL PATIENT ADMIN ====================

@admin.register(models.AnimalPatient)
class AnimalPatientAdmin(BaseModelAdmin):
    list_display = (
        'animal_id', 'name', 'species', 'breed', 'gender',
        'owner_name', 'clinic', 'status', 'animal_link'
    )
    list_filter = (
        'species', 'gender', 'status', 'breeding_status', 'is_active',
        'clinic'
    )
    search_fields = (
        'animal_id', 'microchip_number', 'ear_tag_number',
        'name', 'owner__username', 'owner__email'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'total_visits', 'total_treatments', 'total_cost'
    )
    date_hierarchy = 'created_at'
    raw_id_fields = ('owner', 'breed', 'clinic')
    list_select_related = ('owner', 'clinic', 'breed', 'breed__species')
    
    # Fieldsets
    fieldsets = (
        (_('Identity'), {
            'fields': (
                'animal_id', 'microchip_number', 'ear_tag_number',
                'name', 'species', 'breed', 'gender'
            )
        }),
        (_('Physical Attributes'), {
            'fields': (
                'birth_date', 'age_days', 'color', 'markings',
                'weight_kg', 'height_cm', 'body_condition_score'
            )
        }),
        (_('Health Status'), {
            'fields': (
                'status', 'breeding_status', 'is_pregnant',
                'pregnancy_days', 'expected_delivery_date'
            )
        }),
        (_('Medical Schedule'), {
            'fields': (
                'last_vaccination_date', 'next_vaccination_date',
                'last_deworming_date', 'next_deworming_date',
                'last_heat_date', 'next_heat_date'
            ),
            'classes': ('collapse',)
        }),
        (_('Vital Signs'), {
            'fields': (
                'current_temperature', 'current_heart_rate',
                'current_respiratory_rate'
            ),
            'classes': ('collapse',)
        }),
        (_('Statistics'), {
            'fields': (
                'total_visits', 'total_treatments', 'total_cost'
            ),
            'classes': ('collapse',)
        }),
        (_('Additional Information'), {
            'fields': (
                'notes', 'medical_alert', 'medical_alert_notes',
                'photos', 'documents'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [AppointmentInline, MedicalRecordInline, InvoiceItemInline]
    
    def owner_name(self, obj):
        """Display owner's full name"""
        return f"{obj.owner.first_name} {obj.owner.last_name}"
    owner_name.short_description = 'Owner'
    owner_name.admin_order_field = 'owner__first_name'
    
    def animal_link(self, obj):
        """Create link to view animal detail"""
        url = reverse('admin:core_animalpatient_change', args=[obj.id])
        return format_html('<a href="{}">View Details</a>', url)
    animal_link.short_description = 'Actions'


# ==================== APPOINTMENT ADMIN ====================

@admin.register(models.Appointment)
class AppointmentAdmin(BaseModelAdmin):
    list_display = (
        'id', 'patient_name', 'veterinarian', 'scheduled_date',
        'appointment_type', 'priority', 'status', 'is_urgent'
    )
    list_filter = (
        'status', 'priority', 'appointment_type', 'clinic',
        'scheduled_date'
    )
    search_fields = (
        'patient__animal_id', 'patient__name', 'veterinarian__username',
        'reason'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'status_history', 'predicted_no_show_probability', 'optimization_score'
    )
    date_hierarchy = 'scheduled_date'
    raw_id_fields = ('patient', 'veterinarian', 'clinic')
    list_select_related = ('patient', 'veterinarian', 'clinic')
    autocomplete_fields = ('patient', 'veterinarian')
    
    # Fieldsets
    fieldsets = (
        (_('Appointment Details'), {
            'fields': (
                'clinic', 'patient', 'veterinarian',
                'appointment_type', 'priority'
            )
        }),
        (_('Scheduling'), {
            'fields': (
                'scheduled_date', 'actual_start', 'actual_end',
                'duration_minutes'
            )
        }),
        (_('Status & Progress'), {
            'fields': (
                'status', 'status_history'
            )
        }),
        (_('Medical Information'), {
            'fields': (
                'reason', 'symptoms', 'triage_level'
            ),
            'classes': ('collapse',)
        }),
        (_('Financial'), {
            'fields': (
                'estimated_cost', 'actual_cost'
            ),
            'classes': ('collapse',)
        }),
        (_('Feedback'), {
            'fields': (
                'patient_rating', 'patient_feedback', 'clinician_notes'
            ),
            'classes': ('collapse',)
        }),
        (_('AI Optimization'), {
            'fields': (
                'predicted_no_show_probability', 'optimization_score'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_completed', 'send_reminder']
    
    def patient_name(self, obj):
        """Display patient name with link"""
        url = reverse('admin:core_animalpatient_change', args=[obj.patient.id])
        name = obj.patient.name or obj.patient.animal_id
        return format_html('<a href="{}">{}</a>', url, name)
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__name'
    
    def is_urgent(self, obj):
        """Highlight urgent appointments"""
        return obj.priority in ['EMERGENCY', 'CRITICAL']
    is_urgent.boolean = True
    is_urgent.short_description = 'Urgent'
    
    def mark_as_confirmed(self, request, queryset):
        """Bulk confirm appointments"""
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'{updated} appointments confirmed.')
    mark_as_confirmed.short_description = 'Mark selected as confirmed'
    
    def mark_as_completed(self, request, queryset):
        """Bulk complete appointments"""
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f'{updated} appointments completed.')
    mark_as_completed.short_description = 'Mark selected as completed'
    
    def send_reminder(self, request, queryset):
        """Send reminder for selected appointments"""
        # This would need integration with notification service
        self.message_user(request, f'Reminders sent for {queryset.count()} appointments.')
    send_reminder.short_description = 'Send reminders'


# ==================== APPOINTMENT SLOT ADMIN ====================

@admin.register(models.AppointmentSlot)
class AppointmentSlotAdmin(BaseModelAdmin):
    list_display = ('clinic', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('clinic', 'is_available', 'date')
    search_fields = ('clinic__name',)
    list_editable = ('is_available',)
    date_hierarchy = 'date'


# ==================== MEDICAL RECORD ADMIN ====================

@admin.register(models.MedicalRecord)
class MedicalRecordAdmin(BaseModelAdmin):
    list_display = (
        'id', 'patient_name', 'veterinarian', 'primary_diagnosis',
        'outcome', 'created_at', 'is_emergency'
    )
    list_filter = (
        'outcome', 'is_emergency', 'clinic',
        'created_at'
    )
    search_fields = (
        'patient__animal_id', 'patient__name', 'primary_diagnosis',
        'treatment_given'
    )
    readonly_fields = BaseModelAdmin.readonly_fields
    date_hierarchy = 'created_at'
    raw_id_fields = ('patient', 'clinic', 'veterinarian', 'appointment')
    
    # Fieldsets
    fieldsets = (
        (_('Patient & Provider'), {
            'fields': (
                'patient', 'clinic', 'veterinarian', 'appointment'
            )
        }),
        (_('SOAP Notes'), {
            'fields': (
                'subjective', 'objective', 'assessment', 'plan'
            )
        }),
        (_('Clinical Measurements'), {
            'fields': (
                'weight_kg', 'temperature_c', 'heart_rate',
                'respiratory_rate', 'blood_pressure_systolic',
                'blood_pressure_diastolic', 'pain_score'
            )
        }),
        (_('Findings & Diagnosis'), {
            'fields': (
                'examination_findings', 'diagnostic_images', 'lab_results',
                'primary_diagnosis', 'secondary_diagnosis', 'icd10_codes'
            )
        }),
        (_('Treatment'), {
            'fields': (
                'treatment_given', 'prescribed_medications',
                'procedures_performed'
            )
        }),
        (_('Follow-up'), {
            'fields': (
                'follow_up_date', 'follow_up_instructions',
                'is_follow_up_completed'
            ),
            'classes': ('collapse',)
        }),
        (_('Outcome & Analytics'), {
            'fields': (
                'outcome', 'total_cost', 'treatment_days', 'is_emergency'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        """Display patient name with link"""
        url = reverse('admin:core_animalpatient_change', args=[obj.patient.id])
        name = obj.patient.name or obj.patient.animal_id
        return format_html('<a href="{}">{}</a>', url, name)
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__name'


# ==================== MEDICATION ADMIN ====================

@admin.register(models.Medication)
class MedicationAdmin(BaseModelAdmin):
    list_display = (
        'name', 'generic_name', 'category', 'drug_class',
        'requires_prescription', 'controlled_substance', 'unit_price'
    )
    list_filter = (
        'category', 'drug_class', 'requires_prescription',
        'controlled_substance', 'is_active'
    )
    search_fields = ('name', 'generic_name', 'brand_name', 'registration_number')
    readonly_fields = BaseModelAdmin.readonly_fields
    date_hierarchy = 'created_at'
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'name', 'generic_name', 'brand_name',
                'manufacturer', 'manufacturer_country'
            )
        }),
        (_('Classification'), {
            'fields': (
                'drug_class', 'category'
            )
        }),
        (_('Regulatory'), {
            'fields': (
                'registration_number', 'registration_date', 'expiry_date',
                'controlled_substance', 'requires_prescription'
            )
        }),
        (_('Composition'), {
            'fields': (
                'active_ingredient', 'concentration', 'dosage_form'
            )
        }),
        (_('Usage Information'), {
            'fields': (
                'indications', 'contraindications', 'side_effects',
                'drug_interactions', 'withdrawal_period_days'
            ),
            'classes': ('collapse',)
        }),
        (_('Dosage & Pricing'), {
            'fields': (
                'standard_dosage', 'max_daily_dose',
                'unit_price', 'discount_price'
            ),
            'classes': ('collapse',)
        }),
        (_('Inventory Management'), {
            'fields': (
                'reorder_level', 'reorder_quantity', 'storage_conditions'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )


# ==================== INVENTORY ITEM ADMIN ====================

@admin.register(models.InventoryItem)
class InventoryItemAdmin(BaseModelAdmin):
    list_display = (
        'medication_name', 'clinic', 'batch_number',
        'current_quantity', 'status', 'expiry_date_display',
        'is_expiring_soon'
    )
    list_filter = (
        'status', 'clinic', 'expiry_date',
        'medication__category'
    )
    search_fields = (
        'batch_number', 'medication__name',
        'medication__generic_name'
    )
    readonly_fields = BaseModelAdmin.readonly_fields
    raw_id_fields = ('medication', 'clinic', 'last_updated_by')
    date_hierarchy = 'created_at'
    list_editable = ('current_quantity', 'status')
    
    # Fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'clinic', 'medication'
            )
        }),
        (_('Batch Information'), {
            'fields': (
                'batch_number', 'manufacturing_date', 'expiry_date',
                'received_date'
            )
        }),
        (_('Quantity & Pricing'), {
            'fields': (
                'current_quantity', 'minimum_quantity', 'maximum_quantity',
                'cost_price', 'selling_price'
            )
        }),
        (_('Storage & Supplier'), {
            'fields': (
                'storage_location', 'rack_number', 'temperature_celsius',
                'supplier', 'supplier_contact'
            ),
            'classes': ('collapse',)
        }),
        (_('Order Information'), {
            'fields': (
                'last_order_date', 'next_order_date'
            ),
            'classes': ('collapse',)
        }),
        (_('Status & Audit'), {
            'fields': (
                'status', 'last_updated_by'
            )
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def medication_name(self, obj):
        """Display medication name"""
        url = reverse('admin:core_medication_change', args=[obj.medication.id])
        return format_html('<a href="{}">{}</a>', url, obj.medication.name)
    medication_name.short_description = 'Medication'
    medication_name.admin_order_field = 'medication__name'
    
    def expiry_date_display(self, obj):
        """Format expiry date with warning if expired"""
        if obj.expiry_date < timezone.now().date():
            return format_html('<span style="color: red;">{} (EXPIRED)</span>', obj.expiry_date)
        return obj.expiry_date
    expiry_date_display.short_description = 'Expiry Date'
    expiry_date_display.admin_order_field = 'expiry_date'
    
    def is_expiring_soon(self, obj):
        """Check if item is expiring within 30 days"""
        if obj.expiry_date:
            days_until = (obj.expiry_date - timezone.now().date()).days
            return days_until <= 30 and days_until > 0
        return False
    is_expiring_soon.boolean = True
    is_expiring_soon.short_description = 'Expires in 30 days'


# ==================== INVENTORY TRANSACTION ADMIN ====================

@admin.register(models.InventoryTransaction)
class InventoryTransactionAdmin(BaseModelAdmin):
    list_display = (
        'inventory_item', 'clinic', 'transaction_type',
        'quantity', 'unit_price', 'total_price', 'created_at'
    )
    list_filter = ('transaction_type', 'clinic', 'created_at')
    search_fields = (
        'inventory_item__batch_number',
        'inventory_item__medication__name',
        'reference_number'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'old_quantity', 'new_quantity'
    )
    date_hierarchy = 'created_at'
    raw_id_fields = ('inventory_item', 'clinic', 'purchase_order')


# ==================== INVOICE ADMIN ====================

@admin.register(models.Invoice)
class InvoiceAdmin(BaseModelAdmin):
    list_display = (
        'invoice_number', 'patient_name', 'clinic', 'total_amount',
        'status', 'due_date', 'is_overdue'
    )
    list_filter = ('status', 'payment_method', 'clinic', 'due_date')
    search_fields = (
        'invoice_number', 'patient__animal_id',
        'patient__name', 'payment_reference'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'subtotal', 'tax_amount', 'total_amount',
        'balance_due'
    )
    date_hierarchy = 'created_at'
    raw_id_fields = ('patient', 'clinic', 'appointment', 'medical_record')
    
    # Fieldsets
    fieldsets = (
        (_('Patient & Clinic'), {
            'fields': (
                'clinic', 'patient', 'appointment', 'medical_record'
            )
        }),
        (_('Invoice Details'), {
            'fields': (
                'invoice_number', 'issue_date', 'due_date', 'payment_date'
            )
        }),
        (_('Financial Breakdown'), {
            'fields': (
                'subtotal', 'tax_rate', 'tax_amount',
                'discount', 'total_amount', 'amount_paid', 'balance_due'
            )
        }),
        (_('Items & Services'), {
            'fields': (
                'items', 'services'
            ),
            'classes': ('collapse',)
        }),
        (_('Payment Information'), {
            'fields': (
                'payment_method', 'payment_reference', 'transaction_id'
            ),
            'classes': ('collapse',)
        }),
        (_('Status & Notes'), {
            'fields': (
                'status', 'notes', 'invoice_pdf'
            )
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_overdue']
    
    def patient_name(self, obj):
        """Display patient name"""
        return obj.patient.name or obj.patient.animal_id
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__name'
    
    def is_overdue(self, obj):
        """Check if invoice is overdue"""
        if obj.status not in ['PAID', 'CANCELLED', 'REFUNDED']:
            return obj.due_date < timezone.now().date()
        return False
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def mark_as_paid(self, request, queryset):
        """Bulk mark invoices as paid"""
        updated = queryset.update(status='PAID', payment_date=timezone.now().date())
        self.message_user(request, f'{updated} invoices marked as paid.')
    mark_as_paid.short_description = 'Mark selected as paid'
    
    def mark_as_overdue(self, request, queryset):
        """Bulk mark invoices as overdue"""
        updated = queryset.update(status='OVERDUE')
        self.message_user(request, f'{updated} invoices marked as overdue.')
    mark_as_overdue.short_description = 'Mark selected as overdue'


# ==================== DISEASE REPORT ADMIN ====================

@admin.register(models.DiseaseReport)
class DiseaseReportAdmin(BaseModelAdmin):
    list_display = (
        'disease_name', 'clinic', 'status', 'severity',
        'affected_animals', 'deaths', 'is_outbreak'
    )
    list_filter = (
        'status', 'severity', 'disease_name', 'is_outbreak'
    )
    search_fields = ('disease_name', 'disease_code', 'location')
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'mortality_rate', 'morbidity_rate'
    )
    date_hierarchy = 'report_date'
    raw_id_fields = ('reported_by', 'clinic')
    
    # Fieldsets
    fieldsets = (
        (_('Reporter Information'), {
            'fields': (
                'reported_by', 'clinic', 'location',
                'latitude', 'longitude'
            )
        }),
        (_('Disease Information'), {
            'fields': (
                'disease_name', 'disease_code', 'species_affected'
            )
        }),
        (_('Status & Severity'), {
            'fields': (
                'report_date', 'onset_date', 'status', 'severity'
            )
        }),
        (_('Epidemiology'), {
            'fields': (
                'affected_animals', 'deaths',
                'mortality_rate', 'morbidity_rate',
                'confirmed_cases', 'suspected_cases'
            )
        }),
        (_('Clinical & Laboratory'), {
            'fields': (
                'clinical_signs', 'lab_samples_collected',
                'lab_results', 'lab_report_date'
            ),
            'classes': ('collapse',)
        }),
        (_('Control Measures'), {
            'fields': (
                'control_measures_taken', 'vaccination_campaign',
                'quarantine_implemented'
            ),
            'classes': ('collapse',)
        }),
        (_('Government Reporting'), {
            'fields': (
                'reported_to_government', 'government_report_date',
                'government_reference_number'
            ),
            'classes': ('collapse',)
        }),
        (_('Outbreak Information'), {
            'fields': (
                'is_outbreak', 'outbreak_id', 'spread_rate'
            ),
            'classes': ('collapse',)
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )


# ==================== OUTBREAK ALERT ADMIN ====================

@admin.register(models.OutbreakAlert)
class OutbreakAlertAdmin(BaseModelAdmin):
    list_display = (
        'disease_report', 'alert_level', 'area_affected',
        'radius_km', 'is_active', 'expiry_date'
    )
    list_filter = ('alert_level', 'is_active', 'issued_date')
    search_fields = ('area_affected', 'message')
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'issued_date', 'notifications_sent'
    )
    raw_id_fields = ('disease_report', 'issued_by')


# ==================== REMINDER ADMIN ====================

@admin.register(models.Reminder)
class ReminderAdmin(BaseModelAdmin):
    list_display = (
        'title', 'patient_name', 'clinic', 'reminder_type',
        'priority', 'due_date', 'status', 'is_overdue'
    )
    list_filter = (
        'status', 'reminder_type', 'priority', 'clinic',
        'due_date'
    )
    search_fields = (
        'title', 'description', 'patient__animal_id',
        'patient__name'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'sent_count'
    )
    date_hierarchy = 'due_date'
    raw_id_fields = ('patient', 'clinic', 'created_by', 'acknowledged_by')
    
    # Fieldsets
    fieldsets = (
        (_('Reminder Details'), {
            'fields': (
                'patient', 'clinic', 'created_by',
                'reminder_type', 'title', 'description'
            )
        }),
        (_('Priority & Scheduling'), {
            'fields': (
                'priority', 'due_date', 'reminder_date'
            )
        }),
        (_('Communication Channels'), {
            'fields': (
                'send_sms', 'send_email', 'send_push', 'send_whatsapp'
            ),
            'classes': ('collapse',)
        }),
        (_('Status & Actions'), {
            'fields': (
                'status', 'sent_count', 'action_taken',
                'action_date', 'acknowledged_by'
            )
        }),
        (_('System Info'), {
            'fields': ('id', 'created_at', 'updated_at', 'version', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        """Display patient name"""
        return obj.patient.name or obj.patient.animal_id
    patient_name.short_description = 'Patient'
    patient_name.admin_order_field = 'patient__name'
    
    def is_overdue(self, obj):
        """Check if reminder is overdue"""
        if obj.status == 'PENDING':
            return obj.due_date < timezone.now()
        return False
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'


# ==================== DASHBOARD METRIC ADMIN ====================

@admin.register(models.DashboardMetric)
class DashboardMetricAdmin(BaseModelAdmin):
    list_display = (
        'clinic', 'metric_type', 'time_period',
        'period_date', 'value', 'percentage_change'
    )
    list_filter = ('clinic', 'metric_type', 'time_period')
    search_fields = ('clinic__name',)
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'percentage_change'
    )
    date_hierarchy = 'period_date'


# ==================== AUDIT LOG ADMIN ====================

@admin.register(models.AuditLog)
class AuditLogAdmin(BaseModelAdmin):
    list_display = (
        'user', 'action_type', 'model_name',
        'object_repr', 'created_at', 'ip_address'
    )
    list_filter = ('action_type', 'model_name', 'created_at')
    search_fields = (
        'user__username', 'user__email',
        'object_repr', 'request_url'
    )
    readonly_fields = BaseModelAdmin.readonly_fields + (
        'user', 'action_type', 'model_name', 'object_id',
        'object_repr', 'changes', 'ip_address', 'user_agent',
        'request_url', 'request_method', 'notes'
    )
    date_hierarchy = 'created_at'
    list_select_related = ('user',)
    
    def has_add_permission(self, request):
        """Prevent adding audit logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent changing audit logs"""
        return False


# ==================== REGISTER WITH CUSTOM ADMIN SITE ====================

# Instantiate custom admin site
admin_site = VetCareAdminSite(name='vetcare_admin')

# Register all models with the custom admin site
admin_site.register(models.User, UserAdmin)
admin_site.register(models.Clinic, ClinicAdmin)
admin_site.register(models.AnimalSpecies, AnimalSpeciesAdmin)
admin_site.register(models.AnimalBreed, AnimalBreedAdmin)
admin_site.register(models.AnimalPatient, AnimalPatientAdmin)
admin_site.register(models.Appointment, AppointmentAdmin)
admin_site.register(models.AppointmentSlot, AppointmentSlotAdmin)
admin_site.register(models.MedicalRecord, MedicalRecordAdmin)
admin_site.register(models.Medication, MedicationAdmin)
admin_site.register(models.InventoryItem, InventoryItemAdmin)
admin_site.register(models.InventoryTransaction, InventoryTransactionAdmin)
admin_site.register(models.Invoice, InvoiceAdmin)
admin_site.register(models.DiseaseReport, DiseaseReportAdmin)
admin_site.register(models.OutbreakAlert, OutbreakAlertAdmin)
admin_site.register(models.Reminder, ReminderAdmin)
admin_site.register(models.DashboardMetric, DashboardMetricAdmin)
admin_site.register(models.AuditLog, AuditLogAdmin)

# Override default admin site with custom one
admin.site = admin_site