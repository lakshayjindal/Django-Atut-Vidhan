from django.db import models
from django.contrib.auth.models import AbstractUser
import random
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Adds gender selection and email OTP functionality.
    """
    ...
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    user_gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        db_index=True
    )

    email_otp = models.CharField(max_length=6, blank=True, null=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)

    def generate_otp(self):
        """
        Generates a 6-digit OTP and records the timestamp.
        """
        self.email_otp = f"{random.randint(100000, 999999)}"
        self.otp_sent_at = timezone.now()
        self.save(update_fields=['email_otp', 'otp_sent_at'])


class Profile(models.Model):
    """
    Extended user profile model storing personal, cultural, and professional details.
    """
    GENDER_CHOICES = User.GENDER_CHOICES
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
    age = models.PositiveSmallIntegerField(default=20, db_index=True)  # Small integer saves space
    city = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    state = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    country = models.CharField(max_length=100, default='India', db_index=True)
    phone1 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    height = models.CharField(max_length=30, null=True, blank=True, db_index=True)

    # Cultural / Personal Background
    religion = models.CharField(choices=RELIGION_CHOICES, null=True, blank=True, db_index=True)
    caste = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    gotra = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    mother_tongue = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Education & Profession
    education = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    profession = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    income = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    occupation = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Preferences
    looking_for = models.CharField(choices=LOOKING_FOR_CHOICES, null=True, blank=True, db_index=True)
    bio = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    marital_status = models.CharField(
        choices=[('Single', 'Single'), ('Married', 'Married')],
        null=True, blank=True, db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['gender']),
            models.Index(fields=['city']),
            models.Index(fields=['state']),
            models.Index(fields=['country']),
            models.Index(fields=['religion']),
            models.Index(fields=['profession']),
            models.Index(fields=['looking_for']),
            models.Index(fields=['age']),
        ]

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.user.username})"


class Picture(models.Model):
    """
    Stores URLs of profile or gallery pictures for users.
    Supabase URLs are used instead of ImageField.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pictures", null=True, blank=True)
    picture_url = models.URLField()
    is_profile = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Contact(models.Model):
    """
    Stores user-submitted contact messages.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
