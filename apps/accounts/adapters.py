from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self,request,sociallogin,form =None):
        user = super().save_user(request,sociallogin,form)

        user.role = 'Stakeholder'
        user.is_approved = True
        user.save()

        return user