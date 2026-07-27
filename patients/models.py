from django.db import models
from django.conf import settings

class AnimalSpecies(models.Model):
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=200, null=True, blank=True)
    common_breeds = models.JSONField(default=list)
    
    def __str__(self):
        return self.name

class AnimalPatient(models.Model):
    SPECIES_CHOICES = (
        ('POULTRY', 'Poultry'),
        ('CATTLE', 'Cattle'),
        ('GOAT', 'Goat/Sheep'),
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('HORSE', 'Horse'),
        ('OTHER', 'Other'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('TREATING', 'Under Treatment'),
        ('RECOVERED', 'Recovered'),
        ('DECEASED', 'Deceased'),
        ('REFERRED', 'Referred'),
    )
    
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='patients')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    animal_id = models.CharField(max_length=50, unique=True)  # e.g., N0045
    name = models.CharField(max_length=100, null=True, blank=True)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    age = models.IntegerField(help_text="Age in months")
    weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    identification_tags = models.JSONField(default=dict)  # e.g., ear tag, microchip
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    last_visit = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.animal_id} - {self.name or self.species}"
    
    class Meta:
        ordering = ['-created_at']