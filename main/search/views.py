from django.http import JsonResponse
from django.template.loader import render_to_string
from user.models import Profile
def ajax_search_profiles(request):
    qs = Profile.objects.select_related("user").all()

    # Filters (same as before)
    q = request.GET.get('q')
    city = request.GET.get('city')
    profession = request.GET.get('profession')
    gender = request.GET.get('gender')
    marital_status = request.GET.get('marital_status')
    age_min = request.GET.get('age_min')
    age_max = request.GET.get('age_max')

    if q:
        qs = qs.filter(full_name__icontains=q)
    if city:
        qs = qs.filter(city__icontains=city)
    if profession:
        qs = qs.filter(profession__icontains=profession)
    if gender:
        qs = qs.filter(gender=gender)
    if marital_status:
        qs = qs.filter(marital_status=marital_status)
    if age_min:
        qs = qs.filter(age__gte=int(age_min))
    if age_max:
        qs = qs.filter(age__lte=int(age_max))

    html = render_to_string("user/partials/_search_results.html", {'profiles': qs})
    return JsonResponse({'html': html})