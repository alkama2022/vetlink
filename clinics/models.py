from django.db import models
from django.conf import settings

class Clinic(models.Model):
    CLINIC_TYPES = (
        ('VET', 'Veterinary Clinic'),
        ('HOSPITAL', 'Animal Hospital'),
        ('MOBILE', 'Mobile Clinic'),
        ('GOVT', 'Government Clinic'),
    )
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    clinic_type = models.CharField(max_length=10, choices=CLINIC_TYPES)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(null=True, blank=True)
    operating_hours = models.JSONField(default=dict)  # {monday: '9-5', ...}
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class ClinicStaff(models.Model):
    ROLE_CHOICES = (
        ('VET', 'Veterinarian'),
        ('NURSE', 'Nurse'),
        ('RECEPTIONIST', 'Receptionist'),
        ('PHARMACIST', 'Pharmacist'),
        ('LAB_TECH', 'Lab Technician'),
    )
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ['clinic', 'user']