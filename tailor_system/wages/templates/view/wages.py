from django.shortcuts import render, redirect
from .models import Tailor, Product, DailyWork
from django.utils import timezone

def dashboard(request):
    return render(request, 'view/dashboard.html')

def base(request):
    return render(request, 'view/base.html')

def add_tailor(request):
    if request.method == 'POST':
        name = request.POST['name']
        phone = request.POST['phone']
        Tailor.objects.create(name=name, phone=phone)
        return redirect('dashboard')
    return render(request, 'view/add_tailor.html')

def add_product(request):
    if request.method == 'POST':
        name = request.POST['name']
        rate = request.POST['rate']
        Product.objects.create(name=name, rate=rate)
        return redirect('dashboard')
    return render(request, 'view/add_product.html')

def record_work(request):
    tailors = Tailor.objects.all()
    products = Product.objects.all()
    if request.method == 'POST':
        tailor_id = request.POST['tailor']
        product_id = request.POST['product']
        qty = int(request.POST['quantity'])
        DailyWork.objects.create(
            tailor_id=tailor_id, product_id=product_id, quantity=qty
        )
        return redirect('dashboard')
    return render(request, 'view/record_work.html', {'tailors': tailors, 'products': products})

def daily_report(request):
    today = timezone.now().date()
    work = DailyWork.objects.filter(date=today)
    return render(request, 'view/daily_report.html', {'work': work, 'date': today})
