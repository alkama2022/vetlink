from django.db import models
from django.conf import settings

class Treatment(models.Model):
    patient = models.ForeignKey('patients.AnimalPatient', on_delete=models.CASCADE, related_name='treatments')
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='treatments')
    veterinarian = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='treatments')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, related_name='treatments')
    
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    prescribed_medications = models.JSONField(default=list)
    notes = models.TextField(null=True, blank=True)
    
    follow_up_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Treatment for {self.patient} - {self.created_at}"

class Prescription(models.Model):
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name='prescriptions')
    medication = models.ForeignKey('inventory.Medication', on_delete=models.CASCADE)
    dosage = models.CharField(max_length=200)
    frequency = models.CharField(max_length=200)
    duration = models.CharField(max_length=200)
    quantity = models.IntegerField()
    instructions = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class LabTest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    
    patient = models.ForeignKey('patients.AnimalPatient', on_delete=models.CASCADE, related_name='lab_tests')
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='lab_tests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lab_requests')
    test_name = models.CharField(max_length=200)
    test_type = models.CharField(max_length=200)
    sample_type = models.CharField(max_length=100)
    sample_collected_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    results = models.JSONField(default=dict, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)