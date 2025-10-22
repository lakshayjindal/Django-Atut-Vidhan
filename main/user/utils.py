import csv
import datetime
import random
import re
import uuid
import string
from django.contrib.auth import get_user_model

User = get_user_model()
SUPABASE_URL = "https://krtiayhjqgtsruzboour.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtydGlheWhqcWd0c3J1emJvb3VyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzA0NjQ0NywiZXhwIjoyMDY4NjIyNDQ3fQ.W-d9QUi65k6C3MCyn97qhTJInkikVKLU1_NAJgODds0"
SUPABASE_BUCKET = "media"

def generate_username(first_name, last_name):
    """Generate a random username based on parts of first/last name and digits."""
    first_part = (first_name[:2].lower() if first_name else "")
    last_part = (last_name[-2:].lower() if last_name else "")
    random_digits = ''.join(random.choices(string.digits, k=8))
    return f"user{first_part}{last_part}{random_digits}"


def generate_unique_username(first_name, last_name):
    """ Generate a unique username by attempting random combinations. Falls back to UUID-based username if collisions occur. """
    # Try a few times then fallback to uuid-based unique username
    for _ in range(5):
        username = generate_username(first_name, last_name)
        if not User.objects.filter(username=username).exists():
            return username
    return f"user{uuid.uuid4().hex[:10]}"


def parse_date_from_string(date_str):
    if not date_str or not date_str.strip():
        return None
    date_str = re.sub(r'[()]', '', date_str.strip())
    date_str = re.sub(r'\s+', ' ', date_str)
    date_str = date_str.split(' ')[0]

    formats = ["%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            if dt.year > datetime.datetime.now().year:
                dt = dt.replace(year=dt.year - 100)
            return dt.date()
        except ValueError:
            continue
    return None

def clean_phone_number(phone):
    phone = re.sub(r'\D', '', str(phone))
    return phone if len(phone) >= 10 else None

def height_to_inches(height_str):
    match = re.match(r"(\d+)'(\d+)", str(height_str))
    if match:
        return int(match.group(1)) * 12 + int(match.group(2))
    return None

def estimate_dob_from_age(age):
    try:
        age = int(age)
        return datetime.date.today().replace(year=datetime.date.today().year - age, month=1, day=1)
    except:
        return None

def process_csv_row(row):
    username = generate_unique_username()
    dob = parse_date_from_string(row.get('DOB')) or estimate_dob_from_age(row.get('AGE'))
    return {
        "username": username,
        "gender": row.get("Gender", "").strip().capitalize() or "Other",
        "gotra": row.get("Gotra", "").strip().capitalize(),
        "height_inches": height_to_inches(row.get("Height")),
        "age": int(row["AGE"]) if row.get("AGE", "").isdigit() else None,
        "date_of_birth": dob,
        "phone1": clean_phone_number(row.get("Phone No.")),
        "phone2": clean_phone_number(row.get("Phone no. 2")),
        "notes": row.get("extra", "").strip(),
    }

def bulk_import_users(file_path):
    from .models import Profile  # Import here to avoid circular imports
    created_profiles = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = process_csv_row(row)
            user = User.objects.create(username=cleaned["username"])
            profile = Profile.objects.create(
                user=user,
                gender=cleaned["gender"],
                gotra=cleaned["gotra"],
                height_in=cleaned["height_inches"],
                date_of_birth=cleaned["date_of_birth"],
                phone_primary=cleaned["phone1"],
                phone_secondary=cleaned["phone2"],
                notes=cleaned["notes"],
            )
            created_profiles.append(profile)
    return created_profiles


def upload_to_supabase(file, folder="profile_images"):
    """
    Uploads a file-like object or a path-string to Supabase and returns a public URL.
    Attempts to minimize memory use for common Django UploadedFile objects.

    """

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase URL or Key not set")

    # Generate unique filename with extension
    if isinstance(file, UploadedFile):
        file_ext = file.name.split('.')[-1] if '.' in file.name else 'bin'
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_ext}"
        # If file.chunks() exists (large files), stream into bytes to avoid huge memory spike
        try:
            # many Django uploaded files support chunks(); this avoids reading whole content at once
            chunks = []
            for chunk in file.chunks():
                chunks.append(chunk)
            file_bytes = b"".join(chunks)
        except Exception:
            # fallback - small files often support .read()
            file.seek(0)
            file_bytes = file.read()
        content_type = getattr(file, "content_type", None) or "application/octet-stream"

    elif isinstance(file, str):
        file_ext = file.split('.')[-1] if '.' in file else 'bin'
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_ext}"
        with open(file, "rb") as f:
            file_bytes = f.read()
        content_type, _ = mimetypes.guess_type(file)
        if not content_type:
            content_type = "application/octet-stream"

    else:
        raise ValueError("Invalid file type passed to upload_to_supabase")

    # Upload to Supabase (SDK currently expects bytes)
    try:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            unique_filename, file_bytes, {"content-type": content_type}
        )
    except Exception as e:
        # bubble up clear error for easier debugging
        raise RuntimeError(f"Supabase upload error: {str(e)}")

    return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_filename)

