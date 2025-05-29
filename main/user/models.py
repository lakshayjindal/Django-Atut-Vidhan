from django.db import models
from django.contrib.auth.models import AbstractUser

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
    image = models.ImageField(upload_to="profile_images/", blank=True, null=True)


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
    full_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default='India')
    height = models.CharField(max_length=30, null=True, blank=True)
    phone1 = models.CharField(max_length=20, null=True, blank=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    # Cultural / Personal Background
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, null=True, blank=True)
    caste = models.CharField(max_length=100, blank=True, null=True)
    gotra = models.CharField(max_length=100, blank=True, null=True)
    mother_tongue = models.CharField(max_length=100, null=True, blank=True)

    # Education & Profession
    education = models.CharField(max_length=200, null=True, blank=True)
    profession = models.CharField(max_length=200, null=True, blank=True)
    income = models.CharField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)

    # Preferences
    looking_for = models.CharField(max_length=100, choices=LOOKING_FOR_CHOICES, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # Profile Media
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.user.username})"

