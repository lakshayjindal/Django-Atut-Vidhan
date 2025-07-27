from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from connect.models import ConnectionRequest
from .models import Profile
from django.core.files.storage import default_storage
from .models import Profile
from .forms import ProfileForm
import uuid
from supabase import Client, create_client
from django.db.models import Q
# Create your views here.

User = get_user_model()
SUPABASE_URL = "https://krtiayhjqgtsruzboour.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtydGlheWhqcWd0c3J1emJvb3VyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA0NjQ0NywiZXhwIjoyMDY4NjIyNDQ3fQ.W-d9QUi65k6C3MCyn97qhTJInkikVKLU1_NAJgODds0"
SUPABASE_BUCKET = "media"

supabase: Client = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

def login_user(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard') 

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('user_dashboard')
        else:
            error_message = 'Invalid email or password.'
            return render(request, 'user/auth/login.html', {'error_message': error_message})

    return render(request, "user/auth/login.html")
def signup_user(request):

    if request.user.is_authenticated:
        return redirect('user_dashboard')  # Replace with actual dashboard view name

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')

        if User.objects.filter(email=email).exists():
            error_message = 'Email already registered. Try logging in instead.'
            return render(request, 'user/auth/signup.html', {'error_message': error_message})

        user = User.objects.create_user(
            username=email,  # Important: if username field is email
            email=email,
            password=password
        )
        user.first_name = first_name  
        user.last_name = last_name
        user.save()

        login(request, user)  # Log in after successful signup
        return redirect('complete_profile')
    return render(request, 'user/auth/signup.html')
# def entry_user(request):
#     pass


@login_required
def complete_user(request):
    if request.method == "POST":
        user = request.user

        # Handle "other" logic for dropdowns
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

        state = request.POST.get("state")
        if state == "other":
            state = request.POST.get("state_other")

        dob = request.POST.get("dob")
        occupation = request.POST.get("occupation")
        city = request.POST.get("city")
        profile_image = request.FILES.get("profile_image")
        profile_image_url = None

        if profile_image:
            unique_filename = f"{uuid.uuid4().hex}_{profile_image.name}"
            profile_image_url = upload_to_supabase(profile_image, unique_filename)
            user.image = profile_image_url
        if gender:
            user.user_gender = gender
        user.save()
        # Try to get existing profile, else manually create it with all required fields
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = Profile(
                user=user,
                date_of_birth=dob,
                gender=gender,
                religion=religion,
                education=education,
                occupation=occupation,
                income=income,
                city=city,
                state=state
            )
            if profile_image_url:
                profile.image = profile_image_url
            profile.save()
            return redirect("user_dashboard")

        # If profile already exists, update it
        profile.gender = gender
        profile.date_of_birth = dob
        profile.religion = religion
        profile.education = education
        profile.occupation = occupation
        profile.income = income
        profile.city = city
        profile.state = state
        if profile_image:
            profile.image = profile_image
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
        "upsert": True,
    })

    # Make public (optional)
    public_url = supabase.storage.from_(bucket_name).get_public_url(unique_filename)
    return public_url

