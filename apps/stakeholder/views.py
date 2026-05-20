from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import KYCAgentForm
from .models import AgentKYC


@login_required(login_url='/auth/login/')
def agent_kyc_view(request):

    user = request.user

    profile, created = AgentKYC.objects.get_or_create(user=user)

    if created:
        profile.kyc_status = 'not_submitted'
        profile.save()

    # 🚫 STATUS ROUTING (only GET flow)
    if request.method == "GET":

        if profile.kyc_status == 'pending':
            return redirect('stakeholder:request_pending')

        if profile.kyc_status == 'rollback':
            return redirect('stakeholder:missing_doc')

        if profile.kyc_status == 'approved':
            return redirect('stakeholder:approved_agent')

        if profile.kyc_status == 'rejected':
            return redirect('stakeholder:account_locked')

    # ✅ FORM SUBMISSION ONLY
    form = KYCAgentForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == "POST":

        if form.is_valid():
            obj = form.save(commit=False)

            obj.user = user
            obj.kyc_status = 'pending'   # only when user submits new KYC

            obj.save()

            return redirect('stakeholder:request_pending')

    return render(request, 'stakeholder/KYC.html', {
        'form': form,
        'agentkyc': profile
    })


def request_pending(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/request_pending.html', {
        'agentkyc': agentkyc
    })
@login_required(login_url='/auth/login/')
def missing_doc(request):
    
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/missing_doc.html', {
        'agentkyc': agentkyc,
        'admin_comment': agentkyc.admin_comment if agentkyc else ""
    })

@login_required(login_url='/auth/login/')
def approved_agent(request):
    
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/approved_agent.html', {
        'agentkyc': agentkyc,
        'admin_comment': agentkyc.admin_comment if agentkyc else ""
    })
@login_required(login_url='/accounts/login/')
def agent_details(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/agent_details.html', {
        'agentkyc': agentkyc
    })
@login_required(login_url='/accounts/login/')
def account_locked(request):
    agentkyc = AgentKYC.objects.filter(user=request.user).first()

    return render(request, 'stakeholder/account_locked.html', {
        'agentkyc': agentkyc
    })
