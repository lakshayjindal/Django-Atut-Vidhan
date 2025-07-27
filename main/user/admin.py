from django.contrib import admin, messages
from .models import User, Profile
from django import forms
from django.shortcuts import render, redirect, HttpResponse
from django.urls import path
import csv
from django.utils.text import slugify
from datetime import date
from datetime import datetime


admin.site.site_header = "Atut Vidhan Admin"
admin.site.site_title = "Atut Vidhan"
admin.site.index_title = "Welcome to Website Management"

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.action(description="Export selected users and profiles as CSV")
def export_csv(self, request, queryset):
    # Get field names from User and Profile
    user_fields = [field.name for field in User._meta.get_fields() if field.concrete and not field.many_to_many and not field.one_to_many]
    profile_fields = [field.name for field in Profile._meta.get_fields() if field.concrete and field.name != "user"]

    # Prepare CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    header = user_fields + profile_fields
    writer.writerow(header)

    for user in queryset:
        row = []

        # Get user field values
        for field in user_fields:
            value = getattr(user, field, "")
            row.append(value)

        # Get profile field values
        try:
            profile = user.profile
            for field in profile_fields:
                value = getattr(profile, field, "")
                row.append(value)
        except Profile.DoesNotExist:
            row.extend([""] * len(profile_fields))  # fill blanks if profile doesn't exist

        writer.writerow(row)

    return response

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    actions = ['export_csv']
    list_display = ('id', 'first_name', 'last_name')
    export_csv = export_csv
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv, name="import_csv"),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            imported_count = 0

            user_fields = [field.name for field in User._meta.get_fields() if field.concrete and not field.many_to_many and not field.one_to_many]
            profile_fields = [field.name for field in Profile._meta.get_fields() if field.concrete and field.name != "user"]

            for row_num, row in enumerate(reader, start=1):
                try:
                    username = row.get("username") or f"user_{slugify(row.get('full_name', 'anon'))}_{row_num}"
                    user_data = {}
                    profile_data = {}

                    # Assign User fields
                    for field in user_fields:
                        if field == "password":
                            continue  # set manually
                        if field in row and row[field]:
                            user_data[field] = row[field]

                    # Create or get user
                    user, created = User.objects.get_or_create(username=username, defaults=user_data)

                    if created:
                        user.set_password("Welcome123")
                        user.save()

                    # Prepare profile data
                    dob = None  # track DOB separately to calculate age

                    for field in profile_fields:
                        if field in row and row[field]:
                            value = row[field]

                            if field == "date_of_birth":
                                try:
                                    dob = datetime.strptime(value, "%Y-%m-%d").date()
                                    value = dob
                                except:
                                    dob = None
                                    value = None

                            elif field == "created_at":
                                try:
                                    value = datetime.strptime(value, "%Y-%m-%d").date()
                                except:
                                    value = None

                            profile_data[field] = value

                    # Calculate age from DOB, or fallback to 20
                    if "age" in profile_fields:
                        if dob:
                            today = date.today()
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            profile_data["age"] = age
                        elif "age" not in profile_data:
                            profile_data["age"] = 20

                    # Create profile if doesn't exist
                    if created or not hasattr(user, 'profile'):
                        Profile.objects.create(user=user, **profile_data)

                    imported_count += 1

                except Exception as e:
                    print(f"⚠️ Row {row_num} skipped due to error: {e}")
                    continue

            self.message_user(request, f"✅ {imported_count} users with profiles imported successfully.")
            return redirect("..")

        form = CsvImportForm()
        return render(request, "admin/user/csv_form.html", {"form": form})



admin.site.register(Profile)
