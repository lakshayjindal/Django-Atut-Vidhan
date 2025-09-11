from django.shortcuts import render, redirect
from pyexpat.errors import messages
from user.models import Profile
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from user.models import Contact

# Create your views here.
def entry_user(request):
    # if request.user.is_active:
    #     # return redirect('dashboard')
    #     pass
    return render(request, 'user/index.html')


@login_required
def redirect_user_dashboard(request):
    user = request.user
    user_name = user.get_full_name() or user.username
    try:
        user_profile = user.profile
    except Profile.DoesNotExist:
        user_profile = None

    if user_profile:

        matched_profiles = []

        if user_profile:
            preferred_genders = get_opposite_gender(user_profile.gender)

            # Step 0: Start from valid users with names
            base_query = Profile.objects.exclude(user=user).filter(
                Q(user__first_name__isnull=False) & ~Q(user__first_name='') |
                Q(user__last_name__isnull=False) & ~Q(user__last_name='') |
                Q(user__username__isnull=False) & ~Q(user__username='')
            )

            # Step 1: Match opposite gender
            base_query = base_query.filter(gender__in=preferred_genders)

            # Step 2: Age proximity (±5 years)
            if user_profile.age:
                age_min = user_profile.age - 5
                age_max = user_profile.age + 5
                base_query = base_query.filter(age__gte=age_min, age__lte=age_max)

            # Step 3: Looking for
            if user_profile.looking_for:
                base_query = base_query.filter(looking_for__iexact=user_profile.looking_for)

            # Step 4: Location match
            if user_profile.city:
                base_query = base_query.filter(city__iexact=user_profile.city)

            # Step 5: Final limit and order
            matched_profiles = base_query.order_by('-created_at')[:5] if hasattr(Profile, 'created_at') else base_query[
                :5]

            # Fallback
            if not matched_profiles:
                fallback_query = Profile.objects.exclude(user=user).filter(
                    gender__in=preferred_genders,
                    user__is_active=True,
                    user__first_name__isnull=False
                )
                matched_profiles = fallback_query[:5]
        context = {
            'user_name': user_name,
            'matched_profiles': matched_profiles
        }
        print(context)

        return render(request, 'user/user_dashboard.html', context)
    else:
        messages.error(request, "Kindly Complete the profile Before Proceeding Further")
        return redirect("complete_profile")


def get_opposite_gender(gender):
    if gender == 'Male':
        return ['Female']
    elif gender == 'Female':
        return ['Male']
    return ['Male', 'Female']  # For 'Other' or null fallback


def privacy(request):
    return render(request, 'user/brandfiles/privacypolicy.html')


def terms(request):
    return render(request, 'user/brandfiles/terms.html')


def about(request):
    return render(request, 'user/brandfiles/about.html')


def contact(request):
    if request.method == 'POST':
        user = request.user
        name = request.POST['name']
        message = request.POST['message']
        contact_object = Contact()
        contact_object.message = message
        contact_object.user = user
        contact_object.save()
        messages.success(request, 'Your message has been sent.')
        return redirect('user_dashboard')
    return render(request, 'user/brandfiles/contactus.html')

def faq(request):
    return render(request, 'user/brandfiles/faq.html')

def custom_404_view(request, exception=None):
    if "siteadmin" in request.path:
        return redirect('siteadmin')
    return redirect('login')
