from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from .models import *
from django import forms
from django.shortcuts import render, redirect, HttpResponse
from django.urls import path
import csv
from django.utils.text import slugify
import json
from django.utils.safestring import mark_safe
from . import utils
from django.utils.html import format_html
import datetime
from datetime import date
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .views import upload_to_supabase
admin.site.site_header = "Atut Vidhan Admin"
admin.site.site_title = "Atut Vidhan"
admin.site.index_title = "Welcome to Website Management"

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.action(description="Send Login Link to All the selected users")
def send_link(modeladmin, request, queryset):
    sent_count = 0

    for user in queryset:
        if not user.email:
            continue  # skip users with no email

        # Generate secure login link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        login_url = request.build_absolute_uri(
            reverse("magic_login", kwargs={"uidb64": uid, "token": token})
        )

        # Subject + plain fallback
        subject = "🔑 Your One-Click Login Link"
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [user.email]

        text_content = f"""
        Hi {user.first_name or user.username},

        Use the link below to log into your Atut Vidhan account:

        {login_url}

        If you didn't request this, you can ignore it.
        """

        # Styled HTML version
        html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #333;">
          <h2 style="color: #2c5282;">✨ One-Click Login</h2>
          <p>Hi {(user.first_name or user.username).title()},</p>
          <p>We generated a secure login link for your <strong>Atut Vidhan Matrimony</strong> account.</p>
          <p>Click the button below to log in instantly:</p>

          <div style="margin: 20px 0; text-align: center;">
            <a href="{login_url}" style="
              background-color: #38a169;
              color: white;
              padding: 12px 24px;
              border-radius: 6px;
              text-decoration: none;
              font-weight: bold;
              display: inline-block;
            ">Log In</a>
          </div>

          <p style="font-size: 0.9rem; color: #555;">
            This link will expire soon for security reasons. If you didn’t request it, no worries — just ignore this email.
          </p>
          <p style="margin-top: 32px;">With ❤️,<br><strong>Atut Vidhan Team</strong></p>
        </div>
        """

        # Build + send email
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        sent_count += 1

    messages.success(request, f"Login links sent to {sent_count} user(s).")

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
    actions = ['export_csv', 'send_link']
    list_display = ('id', 'first_name', 'last_name', 'username', 'email')
    export_csv = export_csv
    send_link = send_link
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv, name="import_csv"),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST" and "csv_file" in request.FILES:
            # Step 1: Upload CSV and preview
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()
            reader = list(csv.DictReader(decoded_file))

            hidden_rows = json.dumps(reader)

            return render(request, "admin/user/csv_preview.html", {
                "rows": reader,
                "hidden_rows": hidden_rows
            })


        elif request.method == "POST" and "confirm_import" in request.POST:

            rows = json.loads(request.POST.get("rows_json", "[]"))

            imported_count = 0

            user_fields = {

                f.name for f in User._meta.get_fields()

                if f.concrete and not f.many_to_many and not f.one_to_many

            }

            profile_fields = {

                f.name for f in Profile._meta.get_fields()

                if f.concrete and f.name != "user"

            }

            # detect date fields in Profile

            profile_date_fields = {

                f.name for f in Profile._meta.get_fields() if isinstance(f, models.DateField)

            }

            for idx, row in enumerate(rows):

                try:

                    row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

                    user_data = {k: v for k, v in row.items() if k in user_fields and v}

                    profile_data = {k: v for k, v in row.items() if k in profile_fields and v}

                    # --- Handle DOB + Age ---

                    for date_field in profile_date_fields:

                        if profile_data.get(date_field):

                            dob_str = profile_data[date_field]

                            dob_obj = None

                            for fmt in ("%d-%m-%Y", "%Y-%m-%d"):

                                try:

                                    dob_obj = datetime.datetime.strptime(dob_str, fmt).date()

                                    break

                                except ValueError:

                                    continue

                            if dob_obj:

                                profile_data[date_field] = dob_obj

                                # calculate age if not provided

                                if "age" in profile_fields and not profile_data.get("age"):
                                    today = date.today()

                                    age = (

                                            today.year - dob_obj.year

                                            - ((today.month, today.day) < (dob_obj.month, dob_obj.day))

                                    )

                                    profile_data["age"] = age

                            else:

                                # remove invalid dob

                                profile_data.pop(date_field, None)

                    # --- Handle username ---

                    username = (

                            user_data.get("username")

                            or utils.generate_unique_username(row.get("first_name"), row.get("last_name"))

                            or f"user_{slugify(row.get('full_name', 'anon'))}_{idx}"

                    )

                    user, created = User.objects.get_or_create(username=username, defaults=user_data)

                    if created:

                        user.set_password("Welcome123")

                        user.save()

                    else:

                        for k, v in user_data.items():
                            setattr(user, k, v)

                        user.save()

                    # --- Handle Profile ---

                    Profile.objects.update_or_create(user=user, defaults=profile_data)

                    imported_count += 1


                except Exception as e:

                    print("⚠️ Import error:", e)

                    continue

            self.message_user(request, f"✅ {imported_count} user(s) imported successfully (with profiles).")

            return redirect("..")

        # First-time GET request
        form = CsvImportForm()
        return render(request, "admin/user/csv_form.html", {"form": form})





@admin.register(Profile)
class ProfileModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'age', 'gender', 'phone1', 'phone2')

class UploadImageForm(forms.Form):
    images = forms.FileField()

@admin.register(Picture)
class PictureModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'thumbnail' ,'uploaded_at')
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('upload_images', self.upload_images, name='upload_images')
        ]
        return urls + my_urls
    
    def thumbnail(self, obj):
        if obj.picture_url:
            return format_html(
                '<img src="{}" style="width:50px; height:50px; object-fit:cover; border-radius:4px;" />',
                obj.picture_url
            )
        return "-"
    thumbnail.short_description = "Preview"

    def upload_images(self, request):
        users = User.objects.all()


        if request.method == "POST":
            # Step 1: Handle image uploads
            if request.FILES.getlist("images"):
                for file in request.FILES.getlist("images"):
                    supabase_url = upload_to_supabase(file)
                    Picture.objects.create(picture_url=supabase_url)  # user will be assigned later
                messages.success(request, "Images uploaded. Now map them to users.")
                return redirect("admin:upload_images")  # reload page

            # Step 2: Handle mapping (user assignment + profile pic)
            pictures = Picture.objects.filter(user__isnull=True)
            for picture in pictures:
                user_id = request.POST.get(f"user_{picture.id}")
                if user_id:
                    user = User.objects.get(pk=user_id)
                    picture.user = user
                    picture.save()

            # Step 3: Handle profile picture setting
            for user in users:
                chosen_id = request.POST.get(f"profile_picture_user_{user.id}")
                if chosen_id:
                    pic = Picture.objects.get(pk=chosen_id)
                    # reset all others for this user
                    Picture.objects.filter(user=user, is_profile=True).update(is_profile=False)
                    pic.is_profile = True
                    pic.save()
                    # update User and Profile images

            messages.success(request, "Pictures mapped successfully.")
            return redirect("admin:upload_images")

        # GET request → show upload + mapping form
        pictures = Picture.objects.filter(user__isnull=True)  # only unassigned images
        return render(request, "admin/user/upload_image.html", {
            "users": users,
            "pictures": pictures,
        })