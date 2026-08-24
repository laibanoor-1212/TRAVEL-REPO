from django.shortcuts import render
from packages.models import Package
from packages.models import PackageType 

def home(request):
  
    package_types = PackageType.objects.all().order_by('-id')
    
    context = {
        'package_types': package_types,
    }
    return render(request, 'base/home.html', context)


def about(request):
    return render(request, 'base/about.html')
def contactus(request):
    return render(request, 'base/contactus.html')



def Guide(request):
    return render(request, 'base/Guide.html')
def miqat(request):
    return render(request,'base/miqat.html')
def ahram(request):
    return render(request,'base/ahram.html')
def tawaf(request):
    return render(request,'base/tawaf.html')
def Sai(request):
    return render(request,'base/Sai.html')
def halaq(request):
    return render(request,'base/halaq.html')
def mina(request):
    return render(request,'base/mina.html')
def arafat(request):
    return render(request,'base/arafat.html')
def muzdalifah(request):
    return render(request,'base/muzdalifah.html')
def hajj_guide(request):
    return render(request, 'base/hajj-guide.html')
def iran(request):
    return render(request, 'base/iran.html')
def mashad(request):
    return render(request, 'base/mashad.html')
def qom(request):
    return render(request, 'base/qom.html')
def tehran(request):
    return render(request, 'base/tehran.html')
def karbala(request):
    return render(request, 'base/karbala.html')

def ziyarat(request):
    return render(request, 'base/ziyarat.html')
def nabvi(request):
    return render(request, 'base/nabvi.html')
def riaz(request):
    return render(request, 'base/riaz.html')
def albaqi(request):
    return render(request, 'base/albaqi.html')
def almustarah(request):
    return render(request, 'base/almustarah.html')
def algammamah(request):
    return render(request, 'base/algammamah.html')
def abubakar(request):
    return render(request, 'base/abubakar.html')
def masjidali(request):
    return render(request, 'base/masjidali.html')
def masjidumer(request):
    return render(request,'base/masjidumer.html')
def uhad(request):
    return render(request,'base/uhad.html')

def hajj_packages(request):
    active_packages = Package.objects.filter(status='active').order_by('-created_at')
    
    return render(request, 'packages/hajjpackages.html', {'packages': active_packages})
