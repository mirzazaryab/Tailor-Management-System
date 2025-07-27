# wages/views.py

from django.contrib import messages
from django.http import HttpResponseBadRequest, FileResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Sum, Q, Count, Avg, Subquery, OuterRef
from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date

# Ensure all models are imported
from .models import Tailor, Product, WorkRecord, DailyWork


def dashboard(request):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    total_tailors = Tailor.objects.count()
    total_products = Product.objects.count()

    today_records_qs = DailyWork.objects.filter(date=today)
    today_records = today_records_qs.count()
    today_total = today_records_qs.aggregate(
        total=Sum(F('quantity') * F('rate'))
    )['total'] or Decimal('0.00')

    recent_records = DailyWork.objects.select_related('tailor', 'product').order_by('-date', '-id')[:7]

    top_tailors = DailyWork.objects.filter(date__gte=month_start).values('tailor__name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('rate'))
    ).order_by('-total_amount')[:5]

    weekly_data = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_records = DailyWork.objects.filter(date=day)
        day_total = day_records.aggregate(
            total=Sum(F('quantity') * F('rate'))
        )['total'] or Decimal('0.00')

        weekly_data.append({
            'date': day,
            'total_records': day_records.count(),
            'total_amount': day_total
        })

    weekly_data.reverse()

    context = {
        'today': today,
        'total_tailors': total_tailors,
        'total_products': total_products,
        'today_records': today_records,
        'today_total': today_total,
        'recent_records': recent_records,
        'top_tailors': top_tailors,
        'weekly_data': weekly_data,
    }
    return render(request, 'view/dashboard.html', context)


def base(request):
    return render(request, 'view/base.html')


def add_tailor(request):
    """
    Handles adding new tailors and displaying a paginated, searchable list of existing tailors.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        if name and phone:
            Tailor.objects.create(name=name, phone=phone)
            messages.success(request, f'Tailor "{name}" added successfully!')
            return redirect('add_tailor')
        else:
            messages.error(request, 'Name or phone is required!')

    search_query = request.GET.get('search', '')
    tailors_queryset = Tailor.objects.all()

    if search_query:
        tailors_queryset = tailors_queryset.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    tailors_queryset = tailors_queryset.order_by('name')
    paginator = Paginator(tailors_queryset, 10)
    page_number = request.GET.get('page')
    tailors_page_obj = paginator.get_page(page_number)

    print(f"\n--- DEBUG: add_tailor view ---")
    print(f"Search Query: '{search_query}'")
    print(f"Number of tailors in queryset (before pagination): {tailors_queryset.count()}")
    print(f"Current page number: {tailors_page_obj.number}")
    print(f"Number of tailors on current page: {len(tailors_page_obj)}")
    if tailors_page_obj:
        for i, tailor in enumerate(tailors_page_obj):
            print(f"Tailor {i + 1} on page: ID={tailor.id}, Name='{tailor.name}', Phone='{tailor.phone}'")
    else:
        print("No tailors found on this page (or paginator empty).")
    print(f"--- END DEBUG ---\n")

    return render(request, 'view/add_tailor.html', {
        'tailors': tailors_page_obj,
        'search_query': search_query
    })


def add_product(request):
    """
    Handles adding new products (with default prices) and displaying a paginated,
    searchable list of existing products.
    """
    if request.method == 'POST':
        name = request.POST.get('name')

        if not name:
            messages.error(request, 'Product Name is required.')
        else:
            try:
                Product.objects.create(name=name)
                messages.success(request,
                                 f'Product "{name}" added successfully with default prices. You can edit prices later.')
                return redirect('add_product')
            except Exception as e:
                messages.error(request, f'An error occurred while adding product: {e}')

    search_query = request.GET.get('search', '')
    products_queryset = Product.objects.all()

    if search_query:
        products_queryset = products_queryset.filter(
            Q(name__icontains=search_query)
        )

    products_queryset = products_queryset.order_by('name')
    paginator = Paginator(products_queryset, 10)
    page_number = request.GET.get('page')
    products_page_obj = paginator.get_page(page_number)

    print(f"\n--- DEBUG: add_product view ---")
    print(f"Search Query: '{search_query}'")
    print(f"Number of products in queryset (before pagination): {products_queryset.count()}")
    print(f"Current page number: {products_page_obj.number}")
    print(f"Number of products on current page: {len(products_page_obj)}")
    if products_page_obj:
        for i, product in enumerate(products_page_obj):
            print(
                f"Product {i + 1} on page: ID={product.id}, Name='{product.name}', Tailor Rate='{product.tailor_payment_rate}'")
    else:
        print("No products found on this page (or paginator empty).")
    print(f"--- END DEBUG ---\n")

    return render(request, 'view/add_product.html', {
        'products': products_page_obj,
        'search_query': search_query
    })


def record_work(request):
    tailors = Tailor.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')

    if request.method == 'POST':
        tailor_id = request.POST.get('tailor')
        product_id = request.POST.get('product')
        customer_name = request.POST.get('customer_name')  # ⬅️ NEW FIELD
        qty_str = request.POST.get('quantity')
        work_date = request.POST.get('date')

        if not all([tailor_id, product_id, customer_name, qty_str, work_date]):
            messages.error(request, 'All fields are required including Customer Name.')
            return redirect('record_work')

        try:
            qty = int(qty_str)
            if qty <= 0:
                messages.error(request, 'Quantity must be a positive number.')
                return redirect('record_work')

            tailor = get_object_or_404(Tailor, id=tailor_id)
            product = get_object_or_404(Product, id=product_id)

            DailyWork.objects.create(
                tailor=tailor,
                product=product,
                customer_name=customer_name,  # ⬅️ NEW FIELD
                quantity=qty,
                rate=product.tailor_payment_rate,
                date=work_date,
            )

            messages.success(request, f"Work recorded successfully for '{product.name}' by {tailor.name}.")
            return redirect('record_work')

        except (ValueError, TypeError):
            messages.error(request, 'Invalid quantity or date format.')
            return redirect('record_work')
        except Exception as e:
            messages.error(request, f'An error occurred: {e}')
            return redirect('record_work')

    return render(request, 'view/record_work.html', {
        'tailors': tailors,
        'products': products,
        'today': date.today().isoformat()
    })


def daily_report(request):
    date_str = request.GET.get('date')
    tailor_id = request.GET.get('tailor')

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    tailors = Tailor.objects.all().order_by('name')

    # Fetch DailyWork Records (General Production)
    daily_work_records_queryset = DailyWork.objects.filter(date=selected_date).select_related('tailor', 'product',
                                                                                              'customer')

    daily_work_records_queryset = DailyWork.objects.filter(
        date=selected_date
    ).select_related('tailor', 'product')

    # Apply tailor filter to both querysets if selected
    selected_tailor = None
    if tailor_id:
        try:
            selected_tailor = Tailor.objects.get(id=tailor_id)
            daily_work_records_queryset = daily_work_records_queryset.filter(tailor=selected_tailor)
        except (Tailor.DoesNotExist, ValueError):
            selected_tailor = None

    # Calculate combined totals
    daily_total = daily_work_records_queryset.aggregate(
        total_value=Sum(F('quantity') * F('rate'))
    )['total_value'] or Decimal('0.00')

    grand_total_earnings = daily_total

    total_items_produced = (daily_work_records_queryset.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0)

    context = {
        'daily_work_records': daily_work_records_queryset,
        'tailors': tailors,
        'selected_tailor': selected_tailor,
        'selected_tailor_id': tailor_id,
        'date': selected_date.isoformat(),
        'daily_total': daily_total,
        'grand_total_earnings': grand_total_earnings,
        'total_items_produced': total_items_produced,
    }
    return render(request, 'view/daily_report.html', context)
