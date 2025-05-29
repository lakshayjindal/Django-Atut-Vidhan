from django.contrib import admin, messages
from .models import User, Profile
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
import csv

from .utils import process_csv_row

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
            for row in reader:
                try:
                    cleaned = process_csv_row(row)

                    user, created = User.objects.get_or_create(
                        username=cleaned["username"],
                    )
                    if created:
                        user.set_password("Welcome123")
                        user.user_gender = cleaned["gender"]
                        user.save()
                    if created:
                        Profile.objects.create(
                            user=user,
                            gender=cleaned["gender"],
                            gotra=cleaned["gotra"],
                            height=cleaned["height_inches"],
                            date_of_birth=cleaned["date_of_birth"],
                            phone1=cleaned["phone1"],
                            phone2=cleaned["phone2"],
                            notes=cleaned["notes"],
                        )
                        imported_count += 1

                except Exception as e:
                    # Optional: log or print e to debug bad rows
                    print("Cannot Import due to ", e)
                    continue

            self.message_user(request, f"{imported_count} users imported successfully.")
            return redirect("..")

        form = CsvImportForm()
        return render(request, "admin/user/csv_form.html", {"form": form})

admin.site.register(Profile)
