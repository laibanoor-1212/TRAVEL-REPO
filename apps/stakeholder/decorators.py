from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect, render


def stakeholder_required(view_func):
  @wraps(view_func)
  def _wrapped_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
      messages.info(
          request, 'Please log in or register as an Agent to continue.'
      )
      return redirect('accounts:register')
    if request.user.role == 'user':
      return render(request, 'base/no_acess.html')
    if request.user.role == 'stakeholder':
      if hasattr(request.user, 'stakeholder_profile'):
        if not request.user.stakeholder_profile.is_kyc_completed:
          if request.resolver_match.url_name != 'KYC':
            messages.info(
                request, 'Please complete your KYC verification first.'
            )
            return redirect('stakeholder:KYC')

    return view_func(request, *args, **kwargs)

  return _wrapped_view