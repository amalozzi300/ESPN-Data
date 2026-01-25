from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect


class SuperuserRequiredMixin(UserPassesTestMixin):
    """  
    Mixin for class-based views that require superuser status.
    """
    def test_func(self):
        """  
        Profile must be authenticated, active, and approved.
        """
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.warning(self.request, 'Only site admins may access the requested page.')

        referer = self.request.META.get('HTTP_REFERER')

        if referer:
            return redirect(referer)
        
        return redirect('home')