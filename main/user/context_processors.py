from django.conf import settings

def fallback_images(request):
    return {
        "DEFAULT_FEMALE_FALLBACK_URL": getattr(
            settings,
            "DEFAULT_FEMALE_FALLBACK_URL",
            "https://krtiayhjqgtsruzboour.supabase.co/storage/v1/object/public/media/profile_images/femaledefault.png"
        ),
        "DEFAULT_MALE_FALLBACK_URL": getattr(
            settings,
            "DEFAULT_MALE_FALLBACK_URL",
            "https://krtiayhjqgtsruzboour.supabase.co/storage/v1/object/public/media/profile_images/maledefault.png"
        ),
    }
