from django.shortcuts import render
from packages.models import Package, PackageType 
from adminpanel.models import GuidePage
from .models import ContactMessage

# Helper function to fetch page content dynamically
def get_guide_context(page_slug, page_title):
    page_obj = GuidePage.objects.filter(page_slug=page_slug, is_published=True).first()
    return {
        'guide_page': page_obj,
        'default_title': page_title,
    }
GUIDE_TEMPLATE = 'base/guide_detail.html'
def home(request):
    package_types = PackageType.objects.all().order_by('-id')
    context = {'package_types': package_types}
    return render(request, 'base/home.html', context)

def about(request):
    return render(request, 'base/about.html')



# Dynamic Guide Views
def Guide(request):
    return render(request, 'base/Guide.html', get_guide_context('guide', 'General Guide'))

def miqat(request):
    return render(request, 'base/miqat.html', get_guide_context('miqat', 'Miqat Guide'))

def ahram_guide(request):
    return render(request, 'base/ahram.html', get_guide_context('ahram', 'Ahram Guide'))
def tawaf(request):
    return render(request, 'base/tawaf.html', get_guide_context('tawaf', 'Tawaf Guide'))

def Sai(request):
    return render(request, 'base/Sai.html', get_guide_context('sai', 'Sa\'i Guide'))

def halaq(request):
    return render(request, 'base/halaq.html', get_guide_context('halaq', 'Halaq Guide'))

def mina(request):
    return render(request, 'base/mina.html', get_guide_context('mina', 'Mina Guide'))

def arafat(request):
    return render(request, 'base/arafat.html', get_guide_context('arafat', 'Arafat Guide'))

def muzdalifah(request):
    return render(request, 'base/muzdalifah.html', get_guide_context('muzdalifah', 'Muzdalifah Guide'))

def hajj_guide(request):
    return render(request, 'base/hajj-guide.html', get_guide_context('hajj-guide', 'Hajj Guide'))

def ihram(request):
    return render(request, "base/ihram.html", get_guide_context('ihram', 'Ihram Guide'))

def rami(request):
    return render(request, "base/rami.html", get_guide_context('rami', 'Rami Guide'))

def qurbani(request):
    return render(request, "base/qurbani.html", get_guide_context('qurbani', 'Qurbani Guide'))

def tawaf_ifada(request):
    return render(request, "base/tawaf_ifada.html", get_guide_context('tawaf-ifada', 'Tawaf Ifada Guide'))

def tawaf_wida(request):
    return render(request, "base/tawaf_wida.html", get_guide_context('tawaf-wida', 'Tawaf Wida Guide'))

def iran(request):
    return render(request, 'base/iran.html', get_guide_context('iran', 'Iran Ziyarat'))

def mashad(request):
    return render(request, 'base/mashad.html', get_guide_context('mashad', 'Mashad Ziyarat'))

def qom(request):
    return render(request, 'base/qom.html', get_guide_context('qom', 'Qom Ziyarat'))

def tehran(request):
    return render(request, 'base/tehran.html', get_guide_context('tehran', 'Tehran Ziyarat'))

def karbala(request):
    return render(request, 'base/karbala.html', get_guide_context('karbala', 'Karbala Ziyarat'))

def ziyarat(request):
    return render(request, 'base/ziyarat.html', get_guide_context('ziyarat', 'Ziyarat Guide'))

def nabvi(request):
    return render(request, 'base/nabvi.html', get_guide_context('nabvi', 'Masjid Nabvi Guide'))

def riaz(request):
    return render(request, 'base/riaz.html', get_guide_context('riaz', 'Riaz ul Jannah'))

def albaqi(request):
    return render(request, 'base/albaqi.html', get_guide_context('albaqi', 'Jannat al-Baqi'))

def almustarah(request):
    return render(request, 'base/almustarah.html', get_guide_context('almustarah', 'Masjid Al Mustarah'))

def algammamah(request):
    return render(request, 'base/algammamah.html', get_guide_context('algammamah', 'Masjid Al Gammamah'))

def abubakar(request):
    return render(request, 'base/abubakar.html', get_guide_context('abubakar', 'Masjid Abu Bakar'))

def masjidali(request):
    return render(request, 'base/masjidali.html', get_guide_context('masjidali', 'Masjid Ali'))

def masjidumer(request):
    return render(request, 'base/masjidumer.html', get_guide_context('masjidumer', 'Masjid Umar'))

def uhad(request):
    return render(request, 'base/uhad.html', get_guide_context('uhad', 'Jabal Uhud'))

def hajj_packages(request):
    active_packages = Package.objects.filter(status='active').order_by('-created_at')
    return render(request, 'packages/hajjpackages.html', {'packages': active_packages})


def contactus(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        category = request.POST.get('category')
        message = request.POST.get('message')
        ContactMessage.objects.create(
            name=name,
            email=email,
            category=category,
            message=message
        )

        messages.success(request, "Your message has been sent successfully! Our team will contact you soon.")
        return redirect('base:contactus')  

    return render(request, 'base/contactus.html')