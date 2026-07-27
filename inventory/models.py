from django.db import models
from django.conf import settings

class MedicationCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name

class Medication(models.Model):
    UNIT_CHOICES = (
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('ML', 'Milliliter'),
        ('MG', 'Milligram'),
        ('GM', 'Gram'),
        ('VIAL', 'Vial'),
        ('POUCH', 'Pouch'),
    )
    
    category = models.ForeignKey(MedicationCategory, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, null=True, blank=True)
    manufacturer = models.CharField(max_length=200)
    strength = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    requires_prescription = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.strength}"

class Stock(models.Model):
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='stock')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='stock')
    quantity = models.IntegerField()
    minimum_threshold = models.IntegerField(default=10)
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['clinic', 'medication', 'batch_number']
    
    def __str__(self):
        return f"{self.medication.name} - {self.batch_number} (Stock: {self.quantity})"