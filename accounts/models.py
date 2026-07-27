# from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPES = (
        ('VET', 'Veterinarian'),
        ('CLINIC', 'Clinic'),
        ('FARMER', 'Farmer'),
        ('LAB', 'Lab/Diagnostic'),
        ('GOVT', 'Government Officer'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    phone_number = models.CharField(max_length=15)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    clinic_name = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Nigeria')
    license_number = models.CharField(max_length=50, null=True, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    specialization = models.CharField(max_length=200, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"