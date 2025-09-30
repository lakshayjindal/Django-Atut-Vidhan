"""
Views for user authentication, profile management, and account utilities.
This module contains all user-related views including:
    - Authentication (login, signup, logout, magic login, OTP verification)
    - Profile completion, viewing, and editing
    - File uploads to Supabase
    - Search and profile detail views
    - Password reset flows
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from connect.models import ConnectionRequest
import random
from django.http import JsonResponse
from django.urls import reverse
import string
import mimetypes
import re
from .models import Picture, Profile
from datetime import date, datetime
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.files.storage import default_storage
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
from django.core.files.uploadedfile import UploadedFile

User = get_user_model()
SUPABASE_URL = "https://krtiayhjqgtsruzboour.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtydGlheWhqcWd0c3J1emJvb3VyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA0NjQ0NywiZXhwIjoyMDY4NjIyNDQ3fQ.W-d9QUi65k6C3MCyn97qhTJInkikVKLU1_NAJgODds0"
SUPABASE_BUCKET = "media"

# create client once (already done in original)
supabase: Client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

# Precompiled regexes to avoid recompiling on each request
_EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
_DIGIT_RE = re.compile(r"\D")

def normalize_phone(phone):
    """Cleans phone number by stripping non-digit characters and keeping last 10 digits."""
    if not phone:
        return ""
    digits = _DIGIT_RE.sub("", str(phone))
    # Keep last 10 digits if longer (handles country codes e.g. +91)
    if len(digits) > 10:
        return digits[-10:]
    return digits


def login_user(request):
    """
    Authenticate a user via email, phone, or username.
    Redirects authenticated users to the dashboard. Supports:
        - Email-based login
        - Phone number login (phone1 or phone2 from Profile)
        - Username login as fallback
    """
    # If already logged in, go to dashboard
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        identifier = (request.POST.get('email') or '').strip()
        password = request.POST.get('password')
        user = None

        # 1. Email login
        if _EMAIL_RE.match(identifier):
            # only fetch username to limit DB fetch
            user_obj = User.objects.filter(email__iexact=identifier).only('username').first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

        # 2. Phone login (match against phone1 or phone2)
        elif identifier and any(ch.isdigit() for ch in identifier):
            normalized = normalize_phone(identifier)
            if normalized:
                # single DB lookup using OR to avoid multiple tries
                user_obj = User.objects.filter(
                    Q(profile__phone1__endswith=normalized) |
                    Q(profile__phone2__endswith=normalized)
                ).only('username').select_related('profile').first()
                if user_obj:
                    user = authenticate(request, username=user_obj.username, password=password)

        # 3. Username login (fallback)
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
    """Generate a random username based on parts of first/last name and digits."""
    first_part = (first_name[:2].lower() if first_name else "")
    last_part = (last_name[-2:].lower() if last_name else "")
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"user{first_part}{last_part}{random_digits}"


def generate_unique_username(first_name, last_name):
    """ Generate a unique username by attempting random combinations. Falls back to UUID-based username if collisions occur. """
    # Try a few times then fallback to uuid-based unique username
    for _ in range(5):
        username = generate_username(first_name, last_name)
        if not User.objects.filter(username=username).exists():
            return username
    return f"user{uuid.uuid4().hex[:10]}"


def signup_user(request):
    """
    Handle new user registration:
    - Collects email, password, first/last name
    - Creates an inactive user and generates OTP
    - Sends OTP email and redirects to verification
    """
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()

        # Quick email collision check (case-insensitive)
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "A user with that email already exists.")
            return redirect("signup")

        username = generate_unique_username(first_name, last_name)
        try:
            # create_user is typically fast; keep minimal fields here
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False,
            )
            user.generate_otp()  # store OTP & otp_sent_at on user model
            send_otp_email(user)
            request.session["pending_user_id"] = user.id
            return redirect("verify_otp")
        except IntegrityError:
            messages.error(request, "A user with this email or username already exists.")
            return redirect("signup")

    return render(request, "user/auth/signup.html")


def send_otp_email(user):
    """Send a styled OTP email to the given user using HTML + text content."""
    subject = "✨ Welcome to Atut Vidhan – Your OTP to Begin Your Journey"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    html_content = render_to_string("emails/otp_email.html", {
        "user": user,
        "otp": user.email_otp,
    })
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()


def calculate_age(dob_str):
    """Calculate age in years from a YYYY-MM-DD date string. Return None if invalid."""
    if not dob_str:
        return None
    # Expecting YYYY-MM-DD; guard in case input invalid
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    today = date.today()
    return (
        today.year
        - dob.year
        - ((today.month, today.day) < (dob.month, dob.day))
    )


@login_required
def complete_user(request):
    """
    Handle profile completion:
    - Uploads profile image to Supabase
    - Updates User minimal fields (full_name, gender, age)
    - Updates or creates Profile with additional info
    - Redirects to dashboard on success
    """
    if request.method == "POST":
        user = request.user

        # Profile Image
        profile_image = request.FILES.get("profile_image")
        if profile_image:
            # upload_to_supabase will return a public URL
            profile_image_url = upload_to_supabase(profile_image)
            Picture.objects.create(
                user=user,
                profile_image_url=profile_image_url,
                is_profile=True
            )

        # Basic Inputs
        full_name = (request.POST.get("full_name") or "").strip()
        phone1 = normalize_phone(request.POST.get("phone1"))
        phone2 = normalize_phone(request.POST.get("phone2"))

        # handle dropdowns with 'other' concisely
        def _get_field(base):
            val = request.POST.get(base)
            if val == "other":
                return request.POST.get(f"{base}_other")
            return val

        mother_tongue = _get_field("mother_tongue")
        gender = _get_field("gender")
        religion = _get_field("religion")
        education = _get_field("education")
        income = _get_field("income")
        profession = _get_field("profession")
        state = _get_field("state")
        country = _get_field("country")

        # Remaining Fields
        dob = request.POST.get("dob")
        occupation = request.POST.get("occupation")
        caste = (request.POST.get("caste") or "").strip()
        gotra = (request.POST.get("gotra") or "").strip()
        city = request.POST.get("city")
        bio = (request.POST.get("bio") or "").strip()
        looking_for = request.POST.get("looking_for")

        age = calculate_age(dob)
        if age is None and dob:
            # invalid dob format; ignore age but still store dob raw or handle appropriately
            age = None

        # Update User object minimally
        user_changed = False
        if getattr(user, "full_name", "") != full_name:
            user.full_name = full_name
            user_changed = True
        if getattr(user, "user_gender", "") != gender:
            user.user_gender = gender
            user_changed = True
        if age is not None and getattr(user, "age", None) != age:
            user.age = age
            user_changed = True
        if user_changed:
            # Save only the changed fields
            user.save(update_fields=[f for f in ["full_name", "user_gender", "age"] if hasattr(user, f)])

        # Get or create profile and bulk update fields then save with update_fields
        profile, created = Profile.objects.get_or_create(user=user)

        profile_fields = {
            "full_name": full_name,
            "phone1": phone1,
            "phone2": phone2,
            "date_of_birth": dob,
            "gender": gender,
            "religion": religion,
            "education": education,
            "occupation": occupation,
            "income": income,
            "state": state,
            "city": city,
            "mother_tongue": mother_tongue,
            "profession": profession,
            "looking_for": looking_for or get_opposite_gender(gender),
            "caste": caste,
            "gotra": gotra,
            "bio": bio,
            "country": country,
            "age": age,
        }

        # Assign fields and build update_fields list
        update_fields = []
        for key, value in profile_fields.items():
            if getattr(profile, key, None) != value:
                setattr(profile, key, value)
                update_fields.append(key)

        if update_fields:
            profile.save(update_fields=update_fields)

        return redirect("user_dashboard")

    return render(request, "user/complete_profile.html")


def logout_user(request):
    """Log the user out, clear session, and redirect to login with a success message."""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def view_profile(request):
    """Render the current user’s profile view page."""
    # safe access to related profile (select_related not required because profile is OneToOne)
    profile = request.user.profile
    return render(request, 'user/profile/view.html', {'profile': profile})


@login_required
def edit_profile(request):
    """
    Render and process profile editing:
    - Load up to 6 profile pictures
    - Handle ProfileForm update
    - Handle photo uploads to Supabase
     """
    user = request.user
    profile = user.profile

    # fetch up to 6 pictures only (limit query to needed rows & fields)
    pictures_qs = Picture.objects.filter(user=user).order_by("id").only("id", "picture_url", "is_profile")[:6]
    pictures = list(pictures_qs)
    while len(pictures) < 6:
        pictures.append(None)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

            # Handle new uploaded photos (keys like photos_1, photos_2, etc.)
            uploaded_files = [file for key, file in request.FILES.items() if key.startswith('photos_')]
            for uploaded_file in uploaded_files:
                try:
                    # upload_to_supabase will return a public url
                    file_url = upload_to_supabase(uploaded_file, folder="user_photos")
                    Picture.objects.create(
                        user=user,
                        picture_url=file_url,
                        is_profile=False
                    )
                except Exception as e:
                    # Prefer logging rather than print in production
                    print(f"⚠️ Failed to upload {getattr(uploaded_file, 'name', 'unknown')}: {e}")

            return redirect("view_profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "user/profile/edit.html", {
        "form": form,
        "profile": profile,
        "pictures": pictures,
    })


@login_required
def search_view(request):
    """ Search profiles by query, gender, city, or profession.
    Returns up to 200 profiles for partial rendering. """
    query = (request.GET.get('q') or '').strip()
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

    # limit for safety and only load commonly used fields for display
    profiles = Profile.objects.filter(profile_filters).select_related('user')\
        .only('id', 'full_name', 'city', 'state', 'religion', 'profession', 'bio', 'user__id', 'user__username')[:200]

    return render(request, 'user/partials/_search_results.html', {
        'profiles': profiles,
    })


@login_required
def profile_detail(request, profile_id):
    """ Display details of a target user profile. Checks if the current user is connected to the profile. """
    # get profile and user (single query)
    profile = get_object_or_404(Profile.objects.select_related('user'), id=profile_id)
    target_user = profile.user

    connected = False
    if request.user != target_user:
        # single exists() query checks both directions
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


def upload_to_supabase(file, folder="profile_images"):
    """
    Uploads a file-like object or a path-string to Supabase and returns a public URL.
    Attempts to minimize memory use for common Django UploadedFile objects.

    """

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase URL or Key not set")

    # Generate unique filename with extension
    if isinstance(file, UploadedFile):
        file_ext = file.name.split('.')[-1] if '.' in file.name else 'bin'
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_ext}"
        # If file.chunks() exists (large files), stream into bytes to avoid huge memory spike
        try:
            # many Django uploaded files support chunks(); this avoids reading whole content at once
            chunks = []
            for chunk in file.chunks():
                chunks.append(chunk)
            file_bytes = b"".join(chunks)
        except Exception:
            # fallback - small files often support .read()
            file.seek(0)
            file_bytes = file.read()
        content_type = getattr(file, "content_type", None) or "application/octet-stream"

    elif isinstance(file, str):
        file_ext = file.split('.')[-1] if '.' in file else 'bin'
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_ext}"
        with open(file, "rb") as f:
            file_bytes = f.read()
        content_type, _ = mimetypes.guess_type(file)
        if not content_type:
            content_type = "application/octet-stream"

    else:
        raise ValueError("Invalid file type passed to upload_to_supabase")

    # Upload to Supabase (SDK currently expects bytes)
    try:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            unique_filename, file_bytes, {"content-type": content_type}
        )
    except Exception as e:
        # bubble up clear error for easier debugging
        raise RuntimeError(f"Supabase upload error: {str(e)}")

    return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_filename)


def verify_otp_view(request):
    """
    Handle OTP verification flow:
    - Resend OTP with throttle
    - Verify entered OTP
    - Activate and log in the user on success
    """
    user_id = request.session.get("pending_user_id")
    if not user_id:
        return redirect("signup")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        if "resend" in request.POST:
            # throttle resends to 60 seconds
            if getattr(user, "otp_sent_at", None) and (timezone.now() - user.otp_sent_at) < timedelta(minutes=1):
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
            # Save important fields only
            user.save(update_fields=["is_active", "is_verified", "email_otp"])
            login(request, user)
            request.session.pop("pending_user_id", None)
            return redirect("complete_profile")
        else:
            messages.error(request, "Incorrect OTP. Please try again.")

    return render(request, "user/auth/verify_otp.html", {"email": user.email})


def get_opposite_gender(gender):
    """Return opposite gender string. Defaults to 'Other' if unknown."""
    if gender == "Female":
        return "Male"
    if gender == "Male":
        return "Female"
    return "Other"


def forgot_password_view(request):
    """
    Handle 'forgot password' flow:
    - Accepts email
    - Sends reset link with token to email if user exists
    - Always shows generic success message (for security)
    """
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        user = User.objects.filter(email__iexact=email).first()

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
    """
    Handle password reset:
    - Verify token and user ID
    - Allow password change if valid
    - Send confirmation email on success
    """
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


@login_required
def delete_picture(request, picture_id):
    """Delete a user-owned Picture object via AJAX and return JSON response."""
    picture = get_object_or_404(Picture, id=picture_id, user=request.user)
    picture.delete()
    return JsonResponse({"success": True})


def magic_login(request, uidb64, token):
    """
    Handle magic login via emailed link:
    - Validate token and log user in if valid
    - Show error message if expired or invalid
    """
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name or user.username}! 🎉")
        return redirect("user_dashboard")
    else:
        messages.error(request, "This login link is invalid or has expired.")
        return redirect("login")
