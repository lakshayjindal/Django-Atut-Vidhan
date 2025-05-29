from django.shortcuts import render, redirect
from user.models import Profile
from django.contrib.auth.decorators import login_required
# Create your views here.
def entry_user(request):
    # if request.user.is_active:
    #     # return redirect('dashboard')
    #     pass
    return render(request, 'user/index.html')

@login_required
def redirect_user_dashboard(request):
    user = request.user
    user_name = user.get_full_name() or user.username  # Fallback if full name is empty

    # Get the logged-in user's profile
    try:
        user_profile = user.profile
    except Profile.DoesNotExist:
        user_profile = None

    matched_profiles = []

    if user_profile:
        # Example: Find profiles of opposite gender and what they are looking for matches
        matched_profiles = Profile.objects.filter(
            gender__in=get_opposite_gender(user_profile.gender),
            looking_for__iexact=user_profile.looking_for
        ).exclude(user=user)[:5]

    context = {
        'user_name': user_name,
        'matched_profiles': matched_profiles
    }

    return render(request, 'user/user_dashboard.html', context)

def get_opposite_gender(gender):
    if gender == 'M':
        return ['F']
    elif gender == 'F':
        return ['M']
    return ['M', 'F']  # For 'Other' or null fallback
