from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from connect.models import ConnectionRequest
import random
from django.urls import reverse
import string
import re
from datetime import date, datetime
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.files.storage import default_storage
from .models import Profile
from .forms import ProfileForm
import uuid
from supabase import Client, create_client
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
# Create your views here.

User = get_user_model()
SUPABASE_URL = "https://krtiayhjqgtsruzboour.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtydGlheWhqcWd0c3J1emJvb3VyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA0NjQ0NywiZXhwIjoyMDY4NjIyNDQ3fQ.W-d9QUi65k6C3MCyn97qhTJInkikVKLU1_NAJgODds0"
SUPABASE_BUCKET = "media"

supabase: Client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)


def normalize_phone(phone):
    """Strip spaces, dashes, and country codes from phone input."""
    phone = re.sub(r'\D', '', phone)  # Remove non-digit characters
    if phone.startswith('91') and len(phone) > 10:
        phone = phone[-10:]  # Keep only the last 10 digits
    return phone


def login_user(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('email')
        password = request.POST.get('password')
        user = None

        # 1. Email login
        if re.match(r"[^@]+@[^@]+\.[^@]+", identifier):
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        # 2. Phone login (match against phone1 or phone2)
        elif re.match(r"\d{7,}", identifier):  # crude check that it's digits
            normalized = normalize_phone(identifier)
            try:
                user_obj = User.objects.get(
                    profile__phone1__endswith=normalized
                )
            except User.DoesNotExist:
                try:
                    user_obj = User.objects.get(
                        profile__phone2__endswith=normalized
                    )
                except User.DoesNotExist:
                    user_obj = None

            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

        # 3. Username login
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('user_dashboard')
            else:
                messages.error(request, 'Account inactive. Please verify your email.')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'user/auth/login.html')


def generate_username(first_name, last_name):
    first_part = first_name[:2].lower() if first_name else ""
    last_part = last_name[-2:].lower() if last_name else ""
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"user{first_part}{last_part}{random_digits}"

def generate_unique_username(first_name, last_name):
    for _ in range(5):
        username = generate_username(first_name, last_name)
        if not User.objects.filter(username=username).exists():
            return username
    # Fallback if collisions continue
    return f"user{uuid.uuid4().hex[:10]}"

def signup_user(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        username = generate_unique_username(first_name, last_name)
        if User.objects.filter(email=email).exists():
            messages.error(request, "A user with that email already exists.")
            return redirect("signup")

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )
            user.generate_otp()  # generate and store OTP
            send_otp_email(user)
            request.session["pending_user_id"] = user.id
            return redirect("verify_otp")

        except IntegrityError:
            messages.error(request, "A user with this email or username already exists.")
            return redirect("signup")

    return render(request, "user/auth/signup.html")

def send_otp_email(user):
    subject = "✨ Welcome to Atut Vidhan – Your OTP to Begin Your Journey"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    html_content = render_to_string("emails/otp_email.html", {
        "user": user,
        "otp": user.email_otp,
    })
    text_content = strip_tags(html_content)  # fallback for plain-text email clients

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()


def normalize_phone(phone):
    """Cleans phone number by stripping spaces and non-digit characters."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    # Optionally trim to last 10 digits
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def calculate_age(dob_str):
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date.today()
    return (
        today.year
        - dob.year
        - ((today.month, today.day) < (dob.month, dob.day))
    )

@login_required
def complete_user(request):
    if request.method == "POST":
        user = request.user

        # Profile Image
        profile_image = request.FILES.get("profile_image")
        profile_image_url = upload_to_supabase(profile_image) if profile_image else None

        # Basic Inputs
        full_name = request.POST.get("full_name", "").strip()
        phone1 = normalize_phone(request.POST.get("phone1"))
        phone2 = normalize_phone(request.POST.get("phone2"))

        # Dropdowns with 'other' handling
        mother_tongue = request.POST.get("mother_tongue")
        if mother_tongue == "other":
            mother_tongue = request.POST.get("mother_tongue_other")

        gender = request.POST.get("gender")
        if gender == "other":
            gender = request.POST.get("gender_other")

        religion = request.POST.get("religion")
        if religion == "other":
            religion = request.POST.get("religion_other")

        education = request.POST.get("education")
        if education == "other":
            education = request.POST.get("education_other")

        income = request.POST.get("income")
        if income == "other":
            income = request.POST.get("income_other")

        profession = request.POST.get("profession")
        if profession == "other":
            profession = request.POST.get("profession_other")

        state = request.POST.get("state")
        if state == "other":
            state = request.POST.get("state_other")

        # Remaining Fields
        dob = request.POST.get("dob")
        occupation = request.POST.get("occupation")
        caste = request.POST.get("caste", "").strip()
        gotra = request.POST.get("gotra", "").strip()
        city = request.POST.get("city")
        bio = request.POST.get("bio", "").strip()
        looking_for = request.POST.get("looking_for")
        age = calculate_age(dob)
        # Update User Model
        user.full_name = full_name
        user.user_gender = gender
        user.age = age
        if profile_image_url:
            user.image = profile_image_url
        user.save()

        # Get or create profile
        profile, _ = Profile.objects.get_or_create(user=user)

        # Update profile fields
        profile.full_name = full_name
        profile.phone1 = phone1
        profile.phone2 = phone2
        profile.date_of_birth = dob
        profile.gender = gender
        profile.religion = religion
        profile.education = education
        profile.occupation = occupation
        profile.income = income
        profile.state = state
        profile.city = city
        profile.mother_tongue = mother_tongue
        profile.profession = profession
        profile.looking_for = looking_for or get_opposite_gender(gender)
        profile.caste = caste
        profile.gotra = gotra
        profile.bio = bio
        profile.age = age

        if profile_image_url:
            profile.image = profile_image_url

        profile.save()

        return redirect("user_dashboard")

    return render(request, "user/complete_profile.html")

def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def view_profile(request):
    profile = request.user.profile
    return render(request, 'user/profile/view.html', {'profile': profile})

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('view_profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'user/profile/edit.html', {'form': form})
@login_required
def search_view(request):
    query = request.GET.get('q', '').strip()
    gender = request.GET.get('gender')
    city = request.GET.get('city')
    profession = request.GET.get('profession')

    profile_filters = Q()
    if query:
        profile_filters &= (
            Q(full_name__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query) |
            Q(religion__icontains=query) |
            Q(profession__icontains=query) |
            Q(bio__icontains=query)
        )

    if gender:
        profile_filters &= Q(gender=gender)

    if city:
        profile_filters &= Q(city__icontains=city)

    if profession:
        profile_filters &= Q(profession__icontains=profession)

    profiles = Profile.objects.filter(profile_filters).select_related('user')

    return render(request, 'user/partials/_search_results.html', {
        'profiles': profiles,
    })

@login_required
def profile_detail(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    target_user = profile.user

    # Determine if the logged-in user is connected with this profile
    connected = False
    if request.user != target_user:
        connected = ConnectionRequest.objects.filter(
            (
                Q(sender=request.user, receiver=target_user) |
                Q(sender=target_user, receiver=request.user)
            ),
            is_accepted=True,
            connection_active=True
        ).exists()

    context = {
        'profile': profile,
        'connected': connected,
    }

    return render(request, 'user/profile_detail.html', context)


def upload_to_supabase(file):
    bucket_name = SUPABASE_BUCKET

    # Generate a unique filename
    file_ext = file.name.split('.')[-1]
    unique_filename = f"profile_images/{uuid.uuid4()}.{file_ext}"

    # Save temporarily to disk (required for reading binary content)
    temp_path = default_storage.save(unique_filename, file)
    with default_storage.open(temp_path, 'rb') as f:
        file_bytes = f.read()

    # Upload to Supabase
    response = supabase.storage.from_(bucket_name).upload(unique_filename, file_bytes, {
        "content-type": file.content_type,
    })

    # Make public (optional)
    public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
    return public_url

def verify_otp_view(request):
    user_id = request.session.get("pending_user_id")
    if not user_id:
        return redirect("signup")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        if "resend" in request.POST:
            if user.otp_sent_at and timezone.now() - user.otp_sent_at < timedelta(minutes=1):
                messages.warning(request, "Please wait before resending OTP.")
            else:
                user.generate_otp()
                send_otp_email(user)
                messages.success(request, "✅ OTP resent to your email.")
            return redirect("verify_otp")

        entered_otp = request.POST.get("otp")
        if user.email_otp == entered_otp:
            user.is_active = True
            user.is_verified = True
            user.email_otp = None
            user.save()
            login(request, user)
            if "pending_user_id" in request.session:
                del request.session["pending_user_id"]
            return redirect("complete_profile")  # 🚀 Go to complete profile

        else:
            messages.error(request, "Incorrect OTP. Please try again.")

    return render(request, "user/auth/verify_otp.html", {"email": user.email})


def get_opposite_gender(gender):
    if gender == "Female":
        return "Male"
    elif gender == "Male":
        return "Female"
    return "Other"


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
            )

            subject = "Reset Your Atut Vidhan Password"
            from_email = settings.DEFAULT_FROM_EMAIL
            to = [user.email]

            text_content = f"""
            Hi {user.first_name or user.username},

            You requested to reset your password. Click the link below:

            {reset_url}

            If you didn't make this request, you can safely ignore this email.
            """

            html_content = f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
              <h2 style="color: #2c5282;">🔐 Reset Your Password</h2>
              <p>Hi {user.first_name or user.username},</p>
              <p>We received a request to reset your password for your <strong>Atut Vidhan</strong> account.</p>
              <p>Click the button below to reset it:</p>

              <div style="margin: 20px 0; text-align: center;">
                <a href="{reset_url}" style="
                  background-color: #3182ce;
                  color: white;
                  padding: 12px 24px;
                  border-radius: 6px;
                  text-decoration: none;
                  font-weight: bold;
                  display: inline-block;
                ">Reset Password</a>
              </div>

              <p style="font-size: 0.9rem; color: #555;">
                If you didn’t request this, just ignore this email. Your password will remain unchanged.
              </p>
              <p style="margin-top: 32px;">With ❤️,<br><strong>Atut Vidhan Team</strong></p>
            </div>
            """

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

        messages.success(request, "If that email exists, a reset link has been sent.")
        return redirect('login')

    return render(request, "user/auth/forgot_password.html")


def reset_password_view(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            new_password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            if new_password and new_password == confirm_password:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password reset successful. You can now log in.")
                # Send confirmation email
                subject = "Your Atut Vidhan Password Was Changed ✅"
                from_email = settings.DEFAULT_FROM_EMAIL
                to_email = [user.email]

                text_content = f"""
                Hi {user.first_name or user.username},

                Your Atut Vidhan password was changed successfully.

                If you did not make this change, contact our support immediately.
                """

                html_content = f"""
                <div style="font-family: Arial, sans-serif; color: #333;">
                  <h2 style="color: #2f855a;">✅ Password Changed Successfully</h2>
                  <p>Hi {user.first_name or user.username},</p>
                  <p>This is to confirm that your <strong>Atut Vidhan</strong> password was changed.</p>

                  <p style="font-size: 0.9rem; color: #555;">
                    If you didn't change your password, please <a href="mailto:support@atutvidhan.in">contact support</a> immediately.
                  </p>

                  <p style="margin-top: 32px;">Regards,<br><strong>Atut Vidhan Team</strong></p>
                </div>
                """

                msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                return redirect("login")
            else:
                messages.error(request, "Passwords do not match.")
        return render(request, "user/auth/reset_password.html", {"valid": True})
    else:
        return render(request, "user/auth/reset_password.html", {"valid": False})