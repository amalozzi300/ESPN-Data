from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from espndata.profiles.models import Profile


class ProfileCreationAdminForm(UserCreationForm):
    """  
    Admin form for creating new profiles.
    """
    class Meta:
        model = Profile
        fields = ('email', 'first_name', 'last_name')


class ProfileChangeAdminForm(UserChangeForm):
    """  
    Admin form for updating profiles.
    """
    class Meta:
        model = Profile
        fields = '__all__'


@admin.register(Profile)
class ProfileAdmin(UserAdmin):
    """  
    Admin interface for managing Profile accounts.
    """
    model = Profile

    list_display = (
        'email',
        'first_name',
        'last_name',
        'approval_status',
    )
    list_filter = ('approval_status',)
    search_fields = (
        'email',
        'first_name',
        'last_name',
    )
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name'),
        }),
        ('Approval Status', {
            'fields': ('approval_status', 'is_active', 'date_approved'),
            'description': (
                'Use the "Approved selected profiles" action for easy approval. '
                'Approving sets `is_active=True` and records the approval timestamp.'
            ),
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': (
                'email',
                'password1',
                'password2',
                'first_name',
                'last_name',
            ),
            'classes': ('wide',),
        }),
        ('Approval Status', {
            'fields': ('approval_status', 'is_active'),
            'classes': ('wide',),
        }),
    )

    readonly_fields = ('date_joined', 'last_login', 'date_approved')

    actions = ['approve_profiles', 'deny_profiles']

    def approve_profiles(self, request, queryset):
        """  
        Admin action to approve selected Profiles.
        """
        count = 0

        for profile in queryset:
            if profile.approval_status != Profile.ApprovalStatus.APPROVED:
                profile.approve()
                count += 1

        self.message_user(request, f'{count} profile(s) have been approved and can now log in.')

    approve_profiles.short_description = 'Approve selected profiles'

    def deny_profiles(self, request, queryset):
        """  
        Admin action to deny selected profiles.
        """
        count = 0

        for profile in queryset:
            if profile.approval_status != Profile.ApprovalStatus.DENIED:
                profile.deny()
                count += 1

        self.message_user(request, f'{count} profile(s) have been denied.', level='warning')

    deny_profiles.short_description = 'Deny selected profiles'