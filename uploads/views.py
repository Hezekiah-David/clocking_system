import base64
import binascii
import csv
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import StaffSignupForm
from .models import Attendance, Employee, SystemSetting


def is_admin(user):
    employee = getattr(user, 'employee', None)
    return user.is_authenticated and (user.is_superuser or getattr(employee, 'role', '') == Employee.ROLE_ADMIN)


def home(request):
    return redirect('dashboard') if request.user.is_authenticated else redirect('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', ''), password=request.POST.get('password', ''))
        if user and getattr(getattr(user, 'employee', None), 'is_active', True):
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = StaffSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Staff account created. You can now log in.')
        return redirect('login')
    return render(request, 'signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def _today_record(employee):
    return Attendance.objects.filter(employee=employee, attendance_date=timezone.localdate()).first()


def _face_photo(request):
    data_url = request.POST.get('face_image', '')
    prefix = 'data:image/jpeg;base64,'
    if not data_url.startswith(prefix):
        return None
    try:
        image_data = base64.b64decode(data_url[len(prefix):], validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(image_data) > 5 * 1024 * 1024 or not image_data.startswith(b'\xff\xd8\xff'):
        return None
    return ContentFile(image_data, name='face.jpg')


@login_required
def dashboard(request):
    employee = getattr(request.user, 'employee', None)
    if is_admin(request.user) and (not employee or employee.role == Employee.ROLE_ADMIN):
        return redirect('admin_dashboard')
    if not employee:
        messages.error(request, 'Your account is not linked to an employee profile.')
        return redirect('logout')
    return render(request, 'dashboard.html', {
        'employee': employee,
        'today_record': _today_record(employee),
        'history': employee.attendance_records.all()[:10],
        'now': timezone.localtime(),
    })


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.localdate()
    records = Attendance.objects.filter(attendance_date=today).select_related('employee__user')
    total = Employee.objects.filter(is_active=True).count()
    present = records.count()
    return render(request, 'admin_dashboard.html', {
        'records': records,
        'total_employees': total,
        'present_today': present,
        'late_today': records.filter(status=Attendance.STATUS_LATE).count(),
        'absent_today': max(total - present, 0),
        'currently_clocked_in': records.filter(clock_out_time__isnull=True).count(),
        'today': today,
    })


@login_required
@user_passes_test(is_admin)
def employee_list(request):
    employees = Employee.objects.select_related('user').all()
    search = request.GET.get('search', '').strip()
    department = request.GET.get('department', '').strip()
    if search:
        employees = employees.filter(Q(staff_no__icontains=search) | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search))
    if department:
        employees = employees.filter(department=department)
    departments = Employee.objects.values_list('department', flat=True).distinct().order_by('department')
    return render(request, 'employee_list.html', {'employees': employees, 'departments': departments, 'search': search, 'selected_department': department})


@login_required
@user_passes_test(is_admin)
def attendance_records(request):
    date_value = request.GET.get('date', '')
    selected_date = datetime.strptime(date_value, '%Y-%m-%d').date() if date_value else timezone.localdate()
    records = Attendance.objects.filter(attendance_date=selected_date).select_related('employee__user')
    search = request.GET.get('search', '').strip()
    department = request.GET.get('department', '').strip()
    if search:
        records = records.filter(Q(employee__staff_no__icontains=search) | Q(employee__user__first_name__icontains=search) | Q(employee__user__last_name__icontains=search))
    if department:
        records = records.filter(employee__department=department)
    departments = Employee.objects.values_list('department', flat=True).distinct().order_by('department')
    return render(request, 'attendance.html', {'records': records, 'departments': departments, 'selected_date': selected_date, 'search': search, 'selected_department': department})


@login_required
@require_http_methods(['POST'])
def clock_in(request):
    employee = getattr(request.user, 'employee', None)
    photo = _face_photo(request)
    if not employee or not photo:
        messages.error(request, 'Confirm your staff profile and capture your face before clocking in.')
        return redirect('dashboard')
    now = timezone.localtime()
    settings = SystemSetting.current()
    threshold = datetime.combine(now.date(), settings.official_resumption) + timedelta(minutes=settings.grace_period_minutes)
    status = Attendance.STATUS_LATE if now.replace(tzinfo=None) > threshold else Attendance.STATUS_PRESENT
    try:
        record = Attendance.objects.create(employee=employee, attendance_date=now.date(), clock_in_time=now, status=status)
        record.clock_in_face.save(photo.name, photo, save=True)
        messages.success(request, f'Clock-in successful! Status: {status.title()}.')
    except IntegrityError:
        messages.error(request, 'You have already clocked in today.')
    return redirect('dashboard')


@login_required
@require_http_methods(['POST'])
def clock_out(request):
    employee = getattr(request.user, 'employee', None)
    photo = _face_photo(request)
    if not employee or not photo:
        messages.error(request, 'Confirm your staff profile and capture your face before clocking out.')
        return redirect('dashboard')
    record = _today_record(employee)
    if not record:
        messages.error(request, 'No clock-in record found for today.')
    elif record.clock_out_time:
        messages.error(request, 'You have already clocked out today.')
    else:
        record.clock_out_time = timezone.localtime()
        record.clock_out_face.save(photo.name, photo, save=False)
        record.save(update_fields=['clock_out_time', 'clock_out_face'])
        messages.success(request, 'Clock-out successful!')
    return redirect('dashboard')


@login_required
@user_passes_test(is_admin)
def report(request):
    selected_date = request.GET.get('date', '')
    date_value = datetime.strptime(selected_date, '%Y-%m-%d').date() if selected_date else timezone.localdate()
    period = request.GET.get('period', 'day')
    start_date = date_value
    end_date = date_value
    if period == 'week':
        start_date = date_value - timedelta(days=date_value.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = date_value.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    records = Attendance.objects.filter(attendance_date__range=(start_date, end_date)).select_related('employee__user')
    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance-{start_date}-{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Staff No', 'Employee', 'Department', 'Clock In', 'Clock Out', 'Clock In Photo', 'Clock Out Photo', 'Status'])
        for record in records:
            writer.writerow([
                record.employee.staff_no,
                record.employee.display_name,
                record.employee.department,
                record.clock_in_time,
                record.clock_out_time or '',
                record.clock_in_face.name if record.clock_in_face else '',
                record.clock_out_face.name if record.clock_out_face else '',
                record.get_status_display(),
            ])
        return response
    total = Employee.objects.filter(is_active=True).count()
    present = records.values('employee_id').distinct().count()
    return render(request, 'report.html', {'records': records, 'date': date_value, 'start_date': start_date, 'end_date': end_date, 'period': period, 'total': total, 'present': present, 'late': records.filter(status=Attendance.STATUS_LATE).count(), 'absent': max(total - present, 0)})
