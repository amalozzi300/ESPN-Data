from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin


class ApprovedProfileRequiredMixin(UserPassesTestMixin):
    """  
    Mixin for class-based views that require approved profile status.
    """
    def test_func(self):
        """  
        Profile must be authenticated, active, and approved.
        """
        profile = self.request.user

        if not profile.is_authenticated or not profile.is_active:
            return False
        
        return hasattr(profile, 'approval_status') and profile.approval_status == 'APPROVED'
    
    def handle_no_permission(self):
        messages.warning('Only approved users may access this page. If you are an approved user, please log in.')

        return super().handle_no_permission()