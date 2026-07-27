from django.db import models

# Create your models here.

class Veterinarian(models.Model):
    #user = models.OneToOneField(User,on_delete=models.CASCADE, primary_key=True)
    license_number = models.CharField(max_length=100,unique=True)
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=150)
    university = models.CharField(max_length=150)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    consultation_fee = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    is_verified = models.BooleanField(default=False)
    available_online = models.BooleanField(default=False)
    created_at = models.DateTimeField( auto_now_add=True )