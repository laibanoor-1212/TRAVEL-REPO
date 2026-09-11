from django.shortcuts import render, redirect
from packages.models import Package, PackageType 
from adminpanel.models import GuidePage
from .models import ContactMessage
from django.urls import reverse
from stakeholder.models import AgentKYC
from django.db.models import Q, F
from django.utils import timezone
from django.shortcuts import get_object_or_404

# Helper function to fetch page content dynamically
def get_guide_context(page_slug, page_title):
    page_obj = GuidePage.objects.filter(page_slug=page_slug, is_published=True).first()
    return {
        'guide_page': page_obj,
        'default_title': page_title,
    }
GUIDE_TEMPLATE = 'base/guide_detail.html'
def home(request):
    # Dynamic package types query kar ke dynamic list bhejein
    package_types = PackageType.objects.all()
    
    return render(request, 'base/home.html', {
        'package_types': package_types
    })

def about(request):
    return render(request, 'base/about.html')

def no_acess(request):
    return render(request, 'base/no-acess.html')


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
def global_search(request):
    query = request.GET.get('q', '').strip().lower()
    if not query:
        return redirect('base:home')
    if 'package' in query or 'packages' in query:
        packages_url = reverse('base:hajj_packages')
        
        if 'umrah' in query:
            return redirect(f"{packages_url}?category=umrah")
        elif 'ziyarat' in query:
            return redirect(f"{packages_url}?category=ziyarat")
        elif 'hajj' in query:
            return redirect(f"{packages_url}?category=hajj")
        else:
            return redirect(f"{packages_url}?q={query}")
    umrah_guide_keywords = ['umrah guide', 'umrah steps', 'ahram', 'ihram', 'tawaf', 'sai']
    if any(keyword in query for keyword in umrah_guide_keywords) or query == 'umrah':
        return redirect('base:Guide')
    hajj_guide_keywords = ['hajj guide', 'hajj steps', 'mina', 'arafat', 'muzdalifah', 'jamarat']
    if any(keyword in query for keyword in hajj_guide_keywords) or query == 'hajj':
        return redirect('base:hajj-guide')
    iraq_keywords = ['iraq', 'najaf', 'najaf ashraf', 'karbala', 'kazmain', 'samarra', 'iraq guide', 'iraq ziyarat']
    if any(keyword in query for keyword in iraq_keywords):
        return redirect('base:iraq_guide')

    iran_keywords = ['iran', 'mashhad', 'qom', 'tehran', 'shiraz', 'iran guide', 'iran ziyarat']
    if any(keyword in query for keyword in iran_keywords):
        return redirect('base:iran_guide')

    syria_keywords = ['syria', 'sham', 'shaam', 'damascus', 'damishq', 'syria guide', 'syria ziyarat']
    if any(keyword in query for keyword in syria_keywords):
        return redirect('base:syria_guide')
    general_guide_keywords = ['guide', 'guides', 'travel guide', 'ziyarat guide']
    if query in general_guide_keywords or any(k == query for k in general_guide_keywords):
        return redirect(reverse('base:home') + '#guides')  # Ya redirect('base:hajj_guide') kar dein
    booking_keywords = ['my booking', 'booking status', 'my book', 'my orders', 'ticket status', 'escrow status']
    if any(keyword in query for keyword in booking_keywords):
        return redirect('base:user_bookings')
    how_to_book_keywords = ['how to book', 'booking process', 'escrow', 'payment method', 'step']
    if any(keyword in query for keyword in how_to_book_keywords):
        return redirect(reverse('base:home') + '#how-to-book')
    agent_keywords = ['agent', 'agency', 'travel agent', 'agencies']
    if any(keyword in query for keyword in agent_keywords):
        return redirect('base:agent_list')
    packages_url = reverse('base:hajj_packages')
    return redirect(f"{packages_url}?q={query}")


def hajj_packages(request):
    today = timezone.now().date()
    packages = Package.objects.filter(
        status__iexact='active',
        application_deadline__gte=today,
        booked_seats__lt=F('total_seats')
    ).order_by('-created_at')

    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    # URL Parameter se type le rahe hain (e.g. ?type=Umrah ya ?type=Hajj)
    type_param = request.GET.get('type', '').strip()
    tier_filter = request.GET.get('tier', '').strip()
    agent_id = request.GET.get('agent_id', '').strip()

    if agent_id:
        try:
            agent_kyc = AgentKYC.objects.get(id=agent_id)
            packages = packages.filter(
                Q(agency__agency_name__iexact=agent_kyc.agency_name) |
                Q(agency=agent_kyc.user) | 
                Q(agency_id=agent_id)
            )
        except AgentKYC.DoesNotExist:
            packages = packages.none()

    if query:
        packages = packages.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=query) |
            Q(agency__agency_name__icontains=query) |
            Q(package_type__name__icontains=query)
        )

    # Agar URL mein ?type=Hajj ya ?type=Umrah pass hua hai toh DB filter lagayen
    if type_param and type_param.lower() != 'all':
        packages = packages.filter(package_type__name__icontains=type_param)

    if category_filter:
        packages = packages.filter(package_type__name__iexact=category_filter)

    if tier_filter:
        packages = packages.filter(tier__iexact=tier_filter)

    package_types = PackageType.objects.filter(is_active=True)

    context = {
        'packages': packages,
        'package_types': package_types,
        'search_query': query,
        'selected_type': type_param,  # URL parameter context mein bhej rahe hain
    }
    return render(request, 'packages/hajjpackages.html', context)
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
def agent_list(request):
    query = request.GET.get('q', '').strip()
    service_filter = request.GET.get('service', '')
    agencies = AgentKYC.objects.filter(kyc_status='approved')
    if query:
        agencies = agencies.filter(
            Q(agency_name__icontains=query) |
            Q(owner_name__icontains=query) |
            Q(dts_no__icontains=query) |
            Q(iata_no__icontains=query)
        )

    if service_filter == 'hajj':
        agencies = agencies.filter(is_hajj=True)
    elif service_filter == 'ziyarat':
        agencies = agencies.filter(is_ziyarat=True)

    agencies = agencies.order_by('-submitted_at')

    context = {
        'agencies': agencies,
        'query': query,
        'service_filter': service_filter,
    }
    return render(request, 'base/travel_agents.html', context)

def agent_detail(request, pk):
    agent = get_object_or_404(AgentKYC, pk=pk, kyc_status='approved')
    
    context = {
        'agent': agent,
    }
    return render(request, 'base/agent_details.html', context)