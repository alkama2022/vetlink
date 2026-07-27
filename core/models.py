# core/models.py - The Heart of the System

from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.postgres.indexes import GinIndex, BrinIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from decimal import Decimal

# ------------------- BASE ABSTRACT MODELS -------------------

class BaseModel(models.Model):
    """Audit-enabled base model for all entities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                   null=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                   null=True, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)  # Optimistic locking
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at', 'is_active']),
            models.Index(fields=['updated_at', 'is_active']),
        ]

class TenantAwareModel(BaseModel):
    """Multi-tenant base model for clinic isolation"""
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, 
                              related_name='%(class)s_set', db_index=True)
    
    class Meta:
        abstract = True

# ------------------- USER & IDENTITY MANAGEMENT -------------------

class User(BaseModel):
    """Enhanced User Model with RBAC and MFA Support"""
    
    ROLE_CHOICES = (
        ('SYSTEM_ADMIN', 'System Administrator'),
        ('SUPER_ADMIN', 'Super Administrator'), 
        ('CLINIC_ADMIN', 'Clinic Administrator'),
        ('VETERINARIAN', 'Veterinarian'),
        ('VET_TECH', 'Veterinary Technician'),
        ('FARMER', 'Farmer'),
        ('LAB_TECH', 'Lab Technician'),
        ('GOV_OFFICER', 'Government Officer'),
        ('INSURANCE', 'Insurance Agent'),
        ('PHARMACIST', 'Pharmacist'),
    )
    
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    
    # Security
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    is_mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=100, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True)
    last_login_location = JSONField(default=dict)  # GeoIP data
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Profile
    profile_picture = models.ImageField(upload_to='profiles/%Y/%m/', null=True)
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=10, choices=[('M','Male'),('F','Female'),('O','Other')])
    bio = models.TextField(max_length=500)
    
    # Professional
    license_number = models.CharField(max_length=8, unique=True, null=True)
    specialization = ArrayField(models.CharField(max_length=100), default=list)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    
    # Preferences
    language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='Africa/Lagos')
    notification_preferences = JSONField(default=dict)
    
    # Stats
    total_treatments = models.PositiveIntegerField(default=0)
    total_appointments = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['email', 'phone_number']),
            GinIndex(fields=['specialization']),
        ]

class Clinic(BaseModel):
    """Clinic with comprehensive features and analytics"""
    
    CLINIC_TYPES = (
        ('VET', 'Veterinary Clinic'),
        ('HOSPITAL', 'Animal Hospital'),
        ('MOBILE', 'Mobile Clinic'),
        ('GOVT', 'Government Clinic'),
        ('REFERRAL', 'Referral Center'),
        ('EMERGENCY', 'Emergency Center'),
    )
    
    # Basic Info
    name = models.CharField(max_length=200, db_index=True)
    registration_number = models.CharField(max_length=50, unique=True, db_index=True)
    clinic_type = models.CharField(max_length=20, choices=CLINIC_TYPES)
    description = models.TextField()
    established_date = models.DateField()
    
    # Contact
    address_line1 = models.TextField()
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    # Operating Hours (JSON schema)
    operating_hours = JSONField(default=dict)  # {
        # "monday": {"open": "08:00", "close": "18:00", "lunch_start": "12:00", "lunch_end": "13:00"},
        # "tuesday": {"open": "08:00", "close": "18:00"},
        # "special_days": {"2024-12-25": {"closed": true}}
    # }
    
    # Facilities & Services
    facilities = ArrayField(models.CharField(max_length=100), default=list)
    services = ArrayField(models.CharField(max_length=100), default=list)
    specialties = ArrayField(models.CharField(max_length=100), default=list)
    
    # Capacity
    total_rooms = models.PositiveSmallIntegerField(default=0)
    available_rooms = models.PositiveSmallIntegerField(default=0)
    total_staff = models.PositiveSmallIntegerField(default=0)
    max_patients_daily = models.PositiveIntegerField(default=50)
    
    # Subscription & Status
    subscription_plan = models.CharField(max_length=50, default='BASIC')
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    subscription_expiry = models.DateField(null=True)
    
    # Analytics & Performance
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_patients = models.PositiveIntegerField(default=0)
    total_appointments = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active_patients = models.PositiveIntegerField(default=0)
    
    # Settings
    settings = JSONField(default=dict)  # Clinic-specific settings
    
    class Meta:
        db_table = 'clinics'
        indexes = [
            models.Index(fields=['city', 'state']),
            models.Index(fields=['clinic_type', 'is_active']),
            models.Index(fields=['latitude', 'longitude']),  # For geospatial queries
            GinIndex(fields=['facilities']),
            GinIndex(fields=['services']),
        ]

# ------------------- PATIENT & ANIMAL MANAGEMENT -------------------

class AnimalSpecies(BaseModel):
    """Comprehensive species and breed database"""
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    scientific_name = models.CharField(max_length=200)
    common_names = ArrayField(models.CharField(max_length=100), default=list)
    
    # Classification
    class_name = models.CharField(max_length=50)  # Mammalia, Aves, etc.
    order_name = models.CharField(max_length=50)
    family_name = models.CharField(max_length=50)
    
    # Characteristics
    avg_lifespan = models.PositiveSmallIntegerField(help_text="In years")
    avg_weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    gestation_period = models.PositiveSmallIntegerField(help_text="In days", null=True)
    diet_type = models.CharField(max_length=50, choices=[
        ('CARNIVORE', 'Carnivore'),
        ('HERBIVORE', 'Herbivore'),
        ('OMNIVORE', 'Omnivore'),
    ])
    
    # Health
    common_diseases = ArrayField(models.CharField(max_length=200), default=list)
    vaccination_schedule = JSONField(default=dict)
    normal_temperature_range = JSONField(default=dict)  # {"min": 38.0, "max": 39.5}
    normal_heart_rate_range = JSONField(default=dict)
    normal_respiratory_rate_range = JSONField(default=dict)
    
    # Economic
    market_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    feed_cost_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'animal_species'
        indexes = [
            models.Index(fields=['name', 'scientific_name']),
        ]

class AnimalBreed(BaseModel):
    """Detailed breed information"""
    
    species = models.ForeignKey(AnimalSpecies, on_delete=models.CASCADE, related_name='breeds')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)  # Standard breed code
    
    # Characteristics
    avg_weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    coat_color = ArrayField(models.CharField(max_length=50), default=list)
    temperament = models.CharField(max_length=50, choices=[
        ('DOCILE', 'Docile'),
        ('AGRESSIVE', 'Aggressive'),
        ('PLAYFUL', 'Playful'),
        ('CALM', 'Calm'),
    ])
    
    # Productivity
    milk_production_liters = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    egg_production_year = models.PositiveIntegerField(null=True)
    meat_production_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'animal_breeds'
        unique_together = ['species', 'name']

class AnimalPatient(BaseModel):
    """Comprehensive animal patient record with health history"""
    
    SPECIES_CHOICES = [
        ('POULTRY', 'Poultry'),
        ('CATTLE', 'Cattle'),
        ('GOAT', 'Goat/Sheep'),
        ('PIG', 'Pig'),
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('HORSE', 'Horse'),
        ('RABBIT', 'Rabbit'),
        ('FISH', 'Fish'),
        ('EXOTIC', 'Exotic'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('N', 'Neutered'),
        ('S', 'Spayed'),
    ]
    
    BREEDING_STATUS = [
        ('BREEDING', 'Breeding'),
        ('NON_BREEDING', 'Non-Breeding'),
        ('PREGNANT', 'Pregnant'),
        ('LACTATING', 'Lactating'),
        ('DRY', 'Dry'),
    ]
    
    # Identity
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='patients')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='animals')
    animal_id = models.CharField(max_length=50, unique=True, db_index=True)
    microchip_number = models.CharField(max_length=50, unique=True, null=True)
    ear_tag_number = models.CharField(max_length=50, unique=True, null=True)
    
    # Basic Info
    name = models.CharField(max_length=100, blank=True)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES, db_index=True)
    breed = models.ForeignKey(AnimalBreed, on_delete=models.SET_NULL, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, db_index=True)
    birth_date = models.DateField(null=True)
    age_days = models.PositiveIntegerField(null=True)
    
    # Physical Attributes
    color = models.CharField(max_length=100)
    markings = models.TextField(blank=True)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    body_condition_score = models.DecimalField(max_digits=3, decimal_places=1, 
                                               validators=[MinValueValidator(1), MaxValueValidator(9)])
    
    # Health Status
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('TREATING', 'Under Treatment'),
        ('RECOVERED', 'Recovered'),
        ('DECEASED', 'Deceased'),
        ('REFERRED', 'Referred'),
        ('RELOCATED', 'Relocated'),
    ], db_index=True)
    
    breeding_status = models.CharField(max_length=20, choices=BREEDING_STATUS, null=True)
    is_pregnant = models.BooleanField(default=False)
    pregnancy_days = models.PositiveIntegerField(null=True)
    expected_delivery_date = models.DateField(null=True)
    
    # Medical History (Important Dates)
    last_vaccination_date = models.DateField(null=True)
    next_vaccination_date = models.DateField(null=True)
    last_deworming_date = models.DateField(null=True)
    next_deworming_date = models.DateField(null=True)
    last_heat_date = models.DateField(null=True)
    next_heat_date = models.DateField(null=True)
    
    # Statistics
    total_visits = models.PositiveIntegerField(default=0)
    total_treatments = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Vital Signs (Current)
    current_temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    current_heart_rate = models.PositiveIntegerField(null=True)
    current_respiratory_rate = models.PositiveIntegerField(null=True)
    
    # Additional Data
    notes = models.TextField(blank=True)
    medical_alert = models.BooleanField(default=False)
    medical_alert_notes = models.TextField(blank=True)
    photos = ArrayField(models.URLField(), default=list)
    documents = JSONField(default=dict)
    
    class Meta:
        db_table = 'animal_patients'
        indexes = [
            models.Index(fields=['animal_id', 'microchip_number']),
            models.Index(fields=['species', 'status']),
            models.Index(fields=['owner', 'clinic']),
            models.Index(fields=['birth_date', 'age_days']),
            GinIndex(fields=['markings']),
        ]

# ------------------- APPOINTMENT & SCHEDULING -------------------

class Appointment(BaseModel):
    """Intelligent appointment scheduling with AI optimization"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('CHECKED_IN', 'Checked In'),
        ('IN_PROGRESS', 'In Progress'),
        ('ON_HOLD', 'On Hold'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    
    PRIORITY_CHOICES = [
        ('ROUTINE', 'Routine'),
        ('URGENT', 'Urgent'),
        ('EMERGENCY', 'Emergency'),
        ('CRITICAL', 'Critical'),
    ]
    
    APPOINTMENT_TYPE = [
        ('CONSULTATION', 'Consultation'),
        ('CHECKUP', 'Checkup'),
        ('VACCINATION', 'Vaccination'),
        ('SURGERY', 'Surgery'),
        ('DENTAL', 'Dental'),
        ('LAB', 'Laboratory'),
        ('FOLLOWUP', 'Follow-up'),
        ('EMERGENCY', 'Emergency'),
        ('REFERRAL', 'Referral'),
    ]
    
    # Relationships
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='appointments')
    patient = models.ForeignKey(AnimalPatient, on_delete=models.CASCADE, related_name='appointments')
    veterinarian = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    
    # Scheduling
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='ROUTINE')
    scheduled_date = models.DateTimeField(db_index=True)
    actual_start = models.DateTimeField(null=True)
    actual_end = models.DateTimeField(null=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    status_history = JSONField(default=list)  # Audit trail
    
    # Reason & Details
    reason = models.TextField()
    symptoms = JSONField(default=dict)
    triage_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True
    )
    
    # Estimated costs
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Reminders
    reminder_sent = models.BooleanField(default=False)
    reminder_date = models.DateTimeField(null=True)
    
    # Feedback
    patient_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    patient_feedback = models.TextField(blank=True)
    clinician_notes = models.TextField(blank=True)
    
    # AI Optimization
    predicted_no_show_probability = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    optimization_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'appointments'
        indexes = [
            models.Index(fields=['clinic', 'scheduled_date']),
            models.Index(fields=['veterinarian', 'scheduled_date']),
            models.Index(fields=['patient', 'scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['priority', 'scheduled_date']),
        ]

class AppointmentSlot(BaseModel):
    """Dynamic appointment slots for intelligent scheduling"""
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True, db_index=True)
    capacity = models.PositiveIntegerField(default=1)
    booked_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'appointment_slots'
        unique_together = ['clinic', 'date', 'start_time']

# ------------------- MEDICAL RECORDS & TREATMENT -------------------

class MedicalRecord(BaseModel):
    """Complete medical history with FHIR-compliant structure"""
    
    patient = models.ForeignKey(AnimalPatient, on_delete=models.CASCADE, 
                               related_name='medical_records')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, 
                              related_name='medical_records')
    veterinarian = models.ForeignKey(User, on_delete=models.CASCADE, 
                                    related_name='medical_records')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, 
                                   null=True, related_name='medical_records')
    
    # SOAP Format (Standard medical documentation)
    subjective = models.TextField()  # Owner's description
    objective = models.TextField()   # Physical examination findings
    assessment = models.TextField()  # Diagnosis
    plan = models.TextField()        # Treatment plan
    
    # Clinical Measurements
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1)
    heart_rate = models.PositiveIntegerField()
    respiratory_rate = models.PositiveIntegerField()
    blood_pressure_systolic = models.PositiveIntegerField(null=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True)
    pain_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        default=0
    )
    
    # Additional Findings
    examination_findings = JSONField(default=dict)
    diagnostic_images = ArrayField(models.URLField(), default=list)
    lab_results = JSONField(default=dict)
    
    # Diagnosis
    primary_diagnosis = models.CharField(max_length=200)
    secondary_diagnosis = ArrayField(models.CharField(max_length=200), default=list)
    icd10_codes = ArrayField(models.CharField(max_length=20), default=list)  # Standard codes
    
    # Treatment
    treatment_given = models.TextField()
    prescribed_medications = JSONField(default=list)
    procedures_performed = ArrayField(models.CharField(max_length=200), default=list)
    
    # Follow-up
    follow_up_date = models.DateTimeField(null=True)
    follow_up_instructions = models.TextField(blank=True)
    is_follow_up_completed = models.BooleanField(default=False)
    
    # Outcomes
    outcome = models.CharField(max_length=50, choices=[
        ('IMPROVED', 'Improved'),
        ('RECOVERED', 'Recovered'),
        ('UNCHANGED', 'Unchanged'),
        ('DETERIORATED', 'Deteriorated'),
        ('DECEASED', 'Deceased'),
        ('REFERRED', 'Referred'),
    ], null=True)
    
    # Analytics
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    treatment_days = models.PositiveIntegerField(null=True)
    is_emergency = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'medical_records'
        indexes = [
            models.Index(fields=['patient', 'created_at']),
            models.Index(fields=['veterinarian', 'created_at']),
            models.Index(fields=['created_at']),
            GinIndex(fields=['icd10_codes']),
        ]

class Medication(models.Model):
    """Comprehensive medication database with drug interactions"""
    
    # Classification
    drug_class = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=50, choices=[
        ('ANTIBIOTIC', 'Antibiotic'),
        ('ANTIVIRAL', 'Antiviral'),
        ('ANTIPARASITIC', 'Antiparasitic'),
        ('ANTI_INFLAMMATORY', 'Anti-inflammatory'),
        ('VACCINE', 'Vaccine'),
        ('SEDATIVE', 'Sedative'),
        ('HORMONE', 'Hormone'),
        ('SUPPLEMENT', 'Supplement'),
        ('OTHER', 'Other'),
    ])
    
    # Basic Info
    name = models.CharField(max_length=200, db_index=True)
    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    manufacturer = models.CharField(max_length=200)
    manufacturer_country = models.CharField(max_length=100)
    
    # Regulatory
    registration_number = models.CharField(max_length=50, unique=True)
    registration_date = models.DateField()
    expiry_date = models.DateField()
    controlled_substance = models.BooleanField(default=False)
    requires_prescription = models.BooleanField(default=True)
    
    # Composition
    active_ingredient = models.CharField(max_length=200)
    concentration = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=50, choices=[
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('LIQUID', 'Liquid'),
        ('INJECTION', 'Injection'),
        ('POWDER', 'Powder'),
        ('SPRAY', 'Spray'),
        ('TOPICAL', 'Topical'),
    ])
    
    # Usage
    indications = models.TextField()
    contraindications = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    drug_interactions = ArrayField(models.CharField(max_length=200), default=list)
    withdrawal_period_days = models.PositiveIntegerField(null=True)  # For food animals
    
    # Dosage
    standard_dosage = JSONField(default=dict)  # Per species/weight
    max_daily_dose = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Stock Management
    reorder_level = models.PositiveIntegerField(default=10)
    reorder_quantity = models.PositiveIntegerField(default=50)
    storage_conditions = models.TextField()
    
    class Meta:
        db_table = 'medications'
        indexes = [
            models.Index(fields=['name', 'generic_name']),
            models.Index(fields=['drug_class', 'category']),
            GinIndex(fields=['drug_interactions']),
        ]

# ------------------- INVENTORY & SUPPLY CHAIN -------------------

class InventoryItem(BaseModel):
    """Advanced inventory management with batch tracking"""
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='inventory')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='inventory')
    
    # Batch Information
    batch_number = models.CharField(max_length=50, unique=True, db_index=True)
    manufacturing_date = models.DateField()
    expiry_date = models.DateField(db_index=True)
    received_date = models.DateField(auto_now_add=True)
    
    # Quantity
    current_quantity = models.PositiveIntegerField(default=0, db_index=True)
    minimum_quantity = models.PositiveIntegerField(default=10)
    maximum_quantity = models.PositiveIntegerField(default=100)
    
    # Pricing
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Storage
    storage_location = models.CharField(max_length=100)
    rack_number = models.CharField(max_length=20)
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True)
    
    # Supplier
    supplier = models.CharField(max_length=200)
    supplier_contact = models.CharField(max_length=50)
    last_order_date = models.DateField(null=True)
    next_order_date = models.DateField(null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('ACTIVE', 'Active'),
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('EXPIRED', 'Expired'),
        ('DISCONTINUED', 'Discontinued'),
    ], default='ACTIVE', db_index=True)
    
    # Audit Trail
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                       null=True, related_name='inventory_updates')
    
    class Meta:
        db_table = 'inventory_items'
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_number']),
        ]

class InventoryTransaction(BaseModel):
    """Complete audit trail for inventory movements"""
    
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
        ('ADJUSTMENT', 'Adjustment'),
        ('WASTE', 'Waste'),
        ('TRANSFER', 'Transfer'),
    ]
    
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, 
                                      related_name='transactions')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, 
                              related_name='inventory_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    old_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    reference_number = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True)
    
    # Optional FK to related transactions
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.SET_NULL, 
                                      null=True, related_name='transactions')
    
    class Meta:
        db_table = 'inventory_transactions'
        indexes = [
            models.Index(fields=['clinic', 'transaction_type']),
            models.Index(fields=['created_at']),
        ]

# ------------------- FINANCIAL & BILLING -------------------

class Invoice(BaseModel):
    """Comprehensive billing with multiple payment methods"""
    
    INVOICE_STATUS = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('TRANSFER', 'Bank Transfer'),
        ('MOBILE', 'Mobile Money'),
        ('INSURANCE', 'Insurance'),
        ('CREDIT', 'Credit'),
    ]
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='invoices')
    patient = models.ForeignKey(AnimalPatient, on_delete=models.CASCADE, related_name='invoices')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, 
                                   null=True, related_name='invoices')
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.SET_NULL, 
                                      null=True, related_name='invoices')
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    payment_date = models.DateField(null=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Items Breakdown
    items = JSONField(default=list)  # [{description, quantity, unit_price, total}]
    services = JSONField(default=list)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True)
    payment_reference = models.CharField(max_length=100, null=True)
    transaction_id = models.CharField(max_length=100, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='PENDING', db_index=True)
    
    # Additional
    notes = models.TextField(blank=True)
    invoice_pdf = models.URLField(null=True)  # Stored PDF
    
    class Meta:
        db_table = 'invoices'
        indexes = [
            models.Index(fields=['clinic', 'invoice_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['due_date']),
        ]

# ------------------- DISEASE SURVEILLANCE & PUBLIC HEALTH -------------------

class DiseaseReport(BaseModel):
    """Disease surveillance system for public health"""
    
    DISEASE_STATUS = [
        ('SUSPECTED', 'Suspected'),
        ('UNDER_INVESTIGATION', 'Under Investigation'),
        ('CONFIRMED', 'Confirmed'),
        ('NEGATIVE', 'Negative'),
        ('OUTBREAK', 'Outbreak'),
        ('CONTROLLED', 'Controlled'),
        ('RESOLVED', 'Resolved'),
    ]
    
    SEVERITY = [
        ('LOW', 'Low'),
        ('MODERATE', 'Moderate'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Reporter
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disease_reports')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='disease_reports')
    location = models.CharField(max_length=200)  # LGA or specific area
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Disease Information
    disease_name = models.CharField(max_length=200, db_index=True)
    disease_code = models.CharField(max_length=20)  # OIE/FAO standard codes
    species_affected = ArrayField(models.CharField(max_length=50))
    
    # Details
    report_date = models.DateTimeField(auto_now_add=True)
    onset_date = models.DateField()
    status = models.CharField(max_length=20, choices=DISEASE_STATUS, default='SUSPECTED')
    severity = models.CharField(max_length=20, choices=SEVERITY, default='MODERATE')
    
    # Epidemiology
    affected_animals = models.PositiveIntegerField()
    deaths = models.PositiveIntegerField()
    mortality_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    morbidity_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Clinical Signs
    clinical_signs = JSONField(default=list)
    confirmed_cases = models.PositiveIntegerField(default=0)
    suspected_cases = models.PositiveIntegerField(default=0)
    
    # Laboratory
    lab_samples_collected = models.BooleanField(default=False)
    lab_results = models.TextField(blank=True)
    lab_report_date = models.DateField(null=True)
    
    # Control Measures
    control_measures_taken = models.TextField(blank=True)
    vaccination_campaign = models.BooleanField(default=False)
    quarantine_implemented = models.BooleanField(default=False)
    
    # Government Reporting
    reported_to_government = models.BooleanField(default=False)
    government_report_date = models.DateField(null=True)
    government_reference_number = models.CharField(max_length=50, null=True)
    
    # Analytics
    is_outbreak = models.BooleanField(default=False)
    outbreak_id = models.UUIDField(null=True)
    spread_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'disease_reports'
        indexes = [
            models.Index(fields=['disease_name', 'status']),
            models.Index(fields=['reported_date']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['clinic', 'status']),
        ]

class OutbreakAlert(BaseModel):
    """Real-time outbreak monitoring and alert system"""
    
    ALERT_LEVEL = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ALERT', 'Alert'),
        ('EMERGENCY', 'Emergency'),
    ]
    
    disease_report = models.ForeignKey(DiseaseReport, on_delete=models.CASCADE, 
                                      related_name='alerts')
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outbreak_alerts')
    
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVEL)
    message = models.TextField()
    area_affected = models.CharField(max_length=200)
    radius_km = models.PositiveIntegerField()
    
    affected_facilities = ArrayField(models.UUIDField(), default=list)
    affected_farmers = ArrayField(models.UUIDField(), default=list)
    
    issued_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Communication
    notifications_sent = models.PositiveIntegerField(default=0)
    acknowledged_by = ArrayField(models.UUIDField(), default=list)
    
    class Meta:
        db_table = 'outbreak_alerts'
        indexes = [
            models.Index(fields=['alert_level', 'is_active']),
            models.Index(fields=['issued_date']),
        ]

# ------------------- REMINDERS & NOTIFICATIONS -------------------

class Reminder(BaseModel):
    """Intelligent reminder system with multiple channels"""
    
    REMINDER_TYPES = [
        ('VACCINATION', 'Vaccination Due'),
        ('DEWORMING', 'Deworming Due'),
        ('TREATMENT', 'Treatment Follow-up'),
        ('APPOINTMENT', 'Appointment Reminder'),
        ('MEDICATION', 'Medication Reminder'),
        ('HEAT', 'Heat Detection'),
        ('PREGNANCY', 'Pregnancy Check'),
        ('BREEDING', 'Breeding Period'),
        ('ANNUAL_CHECK', 'Annual Check-up'),
        ('CUSTOM', 'Custom Reminder'),
    ]
    
    PRIORITY = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    patient = models.ForeignKey(AnimalPatient, on_delete=models.CASCADE, 
                               related_name='reminders')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='reminders')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reminders')
    
    # Reminder Details
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY, default='MEDIUM')
    
    # Scheduling
    due_date = models.DateTimeField(db_index=True)
    reminder_date = models.DateTimeField(db_index=True)
    sent_count = models.PositiveIntegerField(default=0)
    
    # Channels
    send_sms = models.BooleanField(default=True)
    send_email = models.BooleanField(default=True)
    send_push = models.BooleanField(default=True)
    send_whatsapp = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ], default='PENDING', db_index=True)
    
    # Actions
    action_taken = models.TextField(blank=True)
    action_date = models.DateTimeField(null=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                       null=True, related_name='acknowledged_reminders')
    
    class Meta:
        db_table = 'reminders'
        indexes = [
            models.Index(fields=['patient', 'due_date']),
            models.Index(fields=['reminder_date', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

# ------------------- ANALYTICS & REPORTING -------------------

class DashboardMetric(BaseModel):
    """Pre-computed analytics for real-time dashboards"""
    
    METRIC_TYPES = [
        ('APPOINTMENT', 'Appointment'),
        ('PATIENT', 'Patient'),
        ('TREATMENT', 'Treatment'),
        ('REVENUE', 'Revenue'),
        ('INVENTORY', 'Inventory'),
        ('DISEASE', 'Disease'),
        ('STAFF', 'Staff'),
        ('CUSTOM', 'Custom'),
    ]
    
    TIME_PERIODS = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    time_period = models.CharField(max_length=20, choices=TIME_PERIODS)
    period_date = models.DateField(db_index=True)
    
    # Data
    value = models.DecimalField(max_digits=15, decimal_places=2)
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    percentage_change = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    data_points = JSONField(default=dict)
    
    # Aggregation
    aggregate_type = models.CharField(max_length=50)
    aggregate_value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    
    class Meta:
        db_table = 'dashboard_metrics'
        unique_together = ['clinic', 'metric_type', 'time_period', 'period_date']
        indexes = [
            models.Index(fields=['clinic', 'period_date']),
            models.Index(fields=['metric_type', 'period_date']),
        ]

class AuditLog(BaseModel):
    """Complete audit trail for compliance"""
    
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                            related_name='audit_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.UUIDField()
    object_repr = models.CharField(max_length=200)
    
    # Details
    changes = JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    request_url = models.CharField(max_length=500)
    request_method = models.CharField(max_length=10)
    
    # Additional
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', 'action_type']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['created_at']),
        ]