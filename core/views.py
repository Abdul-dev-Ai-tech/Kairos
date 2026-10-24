import time
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from catalog.models import Product
from .forms import ContactForm
from .models import Banner, Page

def home(request):
    return render(request, 'core/home.html', {
        'featured': Product.objects.published().cards().filter(featured=True)[:4],
        'new_arrivals': Product.objects.published().cards().filter(new_arrival=True)[:4],
        'banners': Banner.objects.filter(active=True),
    })

def page(request, slug):
    return render(request, 'core/page.html', {'page': get_object_or_404(Page, slug=slug)})

def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if time.time() - request.session.get('contact_last_sent', 0) < 60:
            form.add_error(None, 'Please wait a minute before sending another message.')
        else:
            form.save()
            request.session['contact_last_sent'] = time.time()
            messages.success(request, 'Your message is with our team. We will reply using the email you provided.')
            return redirect('contact')
    return render(request, 'core/contact.html', {'form': form})

def robots(request):
    from django.conf import settings
    return HttpResponse('User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /account/\nDisallow: /accounts/\nDisallow: /orders/\nDisallow: /checkout/\nDisallow: /bag/\nSitemap: ' + settings.SITE_URL + '/sitemap.xml\n', content_type='text/plain')

def error_404(request, exception):
    return render(request, '404.html', status=404)

def error_500(request):
    # No database-dependent context: this page still renders during a DB outage.
    from django.template.loader import get_template
    return HttpResponse(get_template('500.html').render({}), status=500)
