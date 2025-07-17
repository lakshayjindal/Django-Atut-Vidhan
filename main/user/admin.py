from django.contrib import admin, messages
from .models import User, Profile
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
import csv
from django.utils.text import slugify
from .utils import process_csv_row
from datetime import datetime

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
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
                    for field in profile_fields:
                        if field in row and row[field]:
                            value = row[field]
                            # Convert date fields
                            if field in ["date_of_birth", "created_at"]:
                                try:
                                    value = datetime.strptime(value, "%Y-%m-%d").date()
                                except:
                                    value = None
                            profile_data[field] = value

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
