from django.db import models
from django.contrib.auth.models import AbstractUser
import random
from django.utils import timezone
# Create your models here.

class User(AbstractUser):
    ...
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    user_gender = models.CharField(
        max_length=50,
        choices=GENDER_CHOICES,
        null=True, blank=True
    )
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    image = models.URLField(blank=True, null=True)
    def generate_otp(self):
        self.email_otp = f"{random.randint(100000, 999999)}"
        self.otp_sent_at = timezone.now()
        self.save()



class Profile(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    age = models.PositiveIntegerField(default=20)
    RELIGION_CHOICES = [
        ('Hindu', 'Hindu'),
        ('Muslim', 'Muslim'),
        ('Christian', 'Christian'),
        ('Sikh', 'Sikh'),
        ('Other', 'Other'),
    ]

    LOOKING_FOR_CHOICES = [
        ('Bride', 'Bride'),
        ('Groom', 'Groom'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Basic Details
    full_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    state = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    country = models.CharField(max_length=100, default='India', db_index=True)
    height = models.CharField(max_length=30, null=True, blank=True, db_index=True)
    phone1 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    # Cultural / Personal Background
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, null=True, blank=True, db_index=True)
    caste = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    gotra = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    mother_tongue = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Education & Profession
    education = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    profession = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    income = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    occupation = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Preferences
    looking_for = models.CharField(max_length=100, choices=LOOKING_FOR_CHOICES, null=True, blank=True, db_index=True)
    bio = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # Profile Media
    image = models.URLField(blank=True, null=True)
    marital_status = models.CharField(max_length=10, null=True, blank=True, db_index=True, choices=[('Single', 'Single'), ("Married", "Married")])
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.user.username})"


