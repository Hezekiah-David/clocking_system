from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from uploads.views import (
    admin_dashboard, attendance_records, clock_in, clock_out, dashboard,
    employee_list, home, login_view, logout_view, report, signup_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('employees/', employee_list, name='employee_list'),
    path('attendance/', attendance_records, name='attendance_records'),
    path('clock-in/', clock_in, name='clock_in'),
    path('clock-out/', clock_out, name='clock_out'),
    path('reports/', report, name='report'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
