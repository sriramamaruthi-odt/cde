import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

OTP_VALIDITY = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5


class State(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name="districts")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = [("state", "name")]

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class Block(models.Model):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="blocks")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = [("district", "name")]

    def __str__(self):
        return f"{self.name}, {self.district.name}"


class Location(models.Model):
    """A place as entered at registration time (block + pincode).

    Kept separate from UserProfile so it can later be shared with
    organizations, which need multiple locations per record. State and
    district are reached via block, since a state has many districts and
    a district has many blocks.
    """

    pincode = models.CharField(
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "Enter a valid 6-digit pincode.")],
    )
    block = models.ForeignKey(Block, on_delete=models.PROTECT, related_name="locations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("block", "pincode")]
        indexes = [models.Index(fields=["pincode"])]

    def __str__(self):
        return f"{self.block} - {self.pincode}"


class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Badge(models.Model):
    class Title(models.TextChoices):
        MENTOR = "Mentor", "Mentor"
        EXPERT = "Expert", "Expert"
        PRACTITIONER = "Practitioner", "Practitioner"
        LEARNER = "Learner", "Learner"

    title = models.CharField(max_length=100, choices=Title.choices, unique=True)

    def __str__(self):
        return self.title


class PhoneOTP(models.Model):
    """A one-time code sent to a phone number to verify it, e.g. during registration.

    Not tied to UserProfile via a foreign key: verification happens before a
    profile exists, keyed on the phone number itself.
    """

    phone_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(r"^\d{10}$", "Enter a valid 10-digit phone number.")],
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["phone_number"])]

    def __str__(self):
        return f"OTP for {self.phone_number}"

    @classmethod
    def issue(cls, phone_number):
        """Create a fresh OTP for `phone_number`, discarding any unverified one."""
        cls.objects.filter(phone_number=phone_number, is_verified=False).delete()
        code = f"{secrets.randbelow(1_000_000):06d}"
        return cls.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=timezone.now() + OTP_VALIDITY,
        )

    def is_expired(self):
        return timezone.now() > self.expires_at

    def verify(self, code):
        """Validate `code` against this OTP, recording the attempt either way."""
        if self.is_verified or self.is_expired() or self.attempts >= OTP_MAX_ATTEMPTS:
            return False
        self.attempts += 1
        if code == self.code:
            self.is_verified = True
            self.save(update_fields=["attempts", "is_verified"])
            return True
        self.save(update_fields=["attempts"])
        return False


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ORG_ADMIN = "org_admin", "Org Admin"
        COORDINATOR = "coordinator", "Coordinator"
        CDE = "cde", "CDE"

    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHERS = "Others", "Others"

    class Education(models.TextChoices):
        NO_EDUCATION = "No Education", "No Education"
        PRIMARY = "Primary", "Primary"
        SECONDARY = "Secondary", "Secondary"
        HIGHER_SECONDARY = "Higher Secondary", "Higher Secondary"
        GRADUATE_AND_ABOVE = "Graduate and above", "Graduate and above"

    # Access level. Admins sit above any single organization; org-admins,
    # coordinators and cde all belong to one (see `organization` below).
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CDE)

    # --- Mandatory fields for a CDE (per registration sheet); optional for
    # other roles, enforced in clean() instead of at the column level so
    # admin/org-admin/coordinator rows don't need them. ---
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    age = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    phone_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r"^\d{10}$", "Enter a valid 10-digit phone number.")],
    )
    # Set once a PhoneOTP for this number has been verified;
    is_phone_verified = models.BooleanField(default=False)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="profiles", null=True, blank=True
    )
    education = models.CharField(max_length=30, choices=Education.choices, blank=True)
    languages = models.ManyToManyField(Language, related_name="profiles", blank=True)
    photograph = models.ImageField(upload_to="profiles/photos/", null=True, blank=True)
    # Every role except ADMIN belongs to an organization.
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="profiles",
        null=True,
        blank=True,
    )

    # --- Optional / supplementary fields ---
    occupation = models.CharField(max_length=255, blank=True)
    no_of_projects = models.PositiveSmallIntegerField(null=True, blank=True)
    no_of_households_touched = models.PositiveIntegerField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, related_name="profiles", blank=True)
    key_projects = models.TextField(blank=True)
    impact_stories_count = models.PositiveSmallIntegerField(null=True, blank=True)
    trust_level_notes = models.TextField(blank=True)
    audio_intro = models.FileField(upload_to="profiles/audio/", blank=True, null=True)

    # Admin-only, per sheet ("BADGE - entry by admin only") - excluded from the
    # registration form itself, set later through the admin site.
    badge = models.ForeignKey(
        Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.role == self.Role.ADMIN:
            if self.organization_id:
                raise ValidationError(
                    {"organization": "A platform admin is not tied to an organization."}
                )
        elif not self.organization_id:
            raise ValidationError({"organization": "This role requires an organization."})

        if self.role == self.Role.CDE:
            required = {
                "gender": self.gender,
                "age": self.age,
                "location": self.location_id,
                "education": self.education,
                "photograph": self.photograph,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValidationError(
                    "CDE registration requires: " + ", ".join(missing)
                )
