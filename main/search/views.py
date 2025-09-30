from django.shortcuts import render
from django.db.models import Q
from user.models import Profile
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required


def search_page(request):
    """
    Render the search page UI where users can enter filters
    to find potential matches.

    Template:
        user/search_page.html

    Context:
        user (User): The currently logged-in user object.
    """
    return render(request, 'user/search_page.html', {'user': request.user})


@login_required
def search_results(request):
    """
    Handle profile search requests based on query parameters.

    Query Parameters:
        q (str, optional): Free-text query to match full_name or bio.
        city (str, optional): City filter (case-insensitive).
        profession (str, optional): Profession filter (case-insensitive).
        gender (str, optional): Gender filter (exact match).
        marital_status (str, optional): Marital status filter (exact match).
        age_min (int, optional): Minimum age filter.
        age_max (int, optional): Maximum age filter.
        page (int, optional): Page number for pagination (default: 1).
        initial (bool, optional): If present, loads initial suggestions 
                                  (opposite gender to logged-in user).

    Behavior:
        - Excludes the current user and superusers from results.
        - If `initial` is provided, loads up to 10 opposite-gender profiles.
        - Otherwise, applies search filters dynamically.
        - Results are paginated with 12 profiles per page.

    Returns:
        HttpResponse: Rendered HTML with partial template 
        (user/partials/_search_results.html) containing:
            profiles (list[Profile]): Profiles for the current page.
            page_obj (Page): Pagination object for navigation.
            paginator (Paginator): Paginator instance.
    """
    query = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    profession = request.GET.get('profession', '').strip()
    gender = request.GET.get('gender', '')
    marital_status = request.GET.get('marital_status', '')
    age_min = request.GET.get('age_min')
    age_max = request.GET.get('age_max')
    page_number = request.GET.get('page', 1)
    initial = request.GET.get('initial')

    filters = Q()
    filters &= ~Q(user=request.user)
    filters &= ~Q(user__is_superuser=True)

    if initial:
        # Show opposite gender profiles initially
        user_gender = getattr(request.user.profile, 'gender', None)
        if user_gender == 'Male':
            filters &= Q(gender='Female')
        elif user_gender == 'Female':
            filters &= Q(gender='Male')
        else:
            filters &= ~Q(gender='')  # fallback for unknown gender

        queryset = Profile.objects.filter(filters).select_related('user')[:10]
        return render(request, 'user/partials/_search_results.html', {
            'profiles': queryset,
            'page_obj': None,
            'paginator': None,
        })

    if query:
        filters &= (
            Q(full_name__icontains=query) |
            Q(bio__icontains=query)
        )
    if city:
        filters &= Q(city__icontains=city)
    if profession:
        filters &= Q(profession__icontains=profession)
    if gender:
        filters &= Q(gender=gender)
    if marital_status:
        filters &= Q(user__marital_status=marital_status)
    if age_min:
        filters &= Q(age__gte=age_min)
    if age_max:
        filters &= Q(age__lte=age_max)

    queryset = Profile.objects.filter(filters).select_related('user')
    paginator = Paginator(queryset, 12)  # 12 profiles per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'user/partials/_search_results.html', {
        'profiles': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
    })