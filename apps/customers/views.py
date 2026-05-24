from django.shortcuts import render

def customer_kyc(request):
    return render(request,'customer/customer_kyc.html')