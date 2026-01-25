from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class ProfileManager(BaseUserManager):
    """  
    Custom manager for email-based Profile (User) model.
    """
    def create_user(self, email, password=None, **extra_fields):
        """  
        Creates, saves, and returns regular profile with given email and password.
        """
        if not email:
            raise ValueError('The Email field is required.')
        
        email = self.normalize_email(email)
        profile = self.model(email=email, **extra_fields)
        profile.set_password(password)
        profile.save(using=self._db)
        
        return profile
    
    def create_superuser(self, email, password=None, **extra_fields):
        """   
        Creates, saves, and returns superuser enabled profile with given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('approval_status', 'APPROVED')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have `is_staff=True`.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have `is_superuser=True`.')

        return self.create_user(email, password, **extra_fields)
    

class Profile(AbstractBaseUser, PermissionsMixin):
    """  
    Custom User model (renamed to Profile) using email as the username field.
    """
    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        DENIED = 'DENIED', 'Denied'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    approval_status = models.CharField(max_length=32, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    date_approved = models.DateTimeField(null=True, blank=True)

    objects = ProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'profile'
        verbose_name_plural = 'profiles'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
    
    def get_short_name(self):
        return self.first_name.strip()
    
    def approve(self):
        """  
        Approves this profile account. After approval, user can log in to their profile.
        """
        self.is_active = True
        self.approval_status = self.ApprovalStatus.APPROVED
        self.date_approved = timezone.now()
        self.save()

    def deny(self):
        """  
        Denies this profile account.
        """
        self.is_active = False
        self.approval_status = self.ApprovalStatus.DENIED
        self.save()