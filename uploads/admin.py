from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .forms import EmployeeAdminForm
from .models import Attendance, Employee, SystemSetting


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeAdminForm
    list_display = ('staff_no', 'display_name', 'department', 'designation', 'role', 'is_active')
    list_filter = ('department', 'role', 'is_active')
    search_fields = ('staff_no', 'user__first_name', 'user__last_name', 'user__username')
    list_editable = ('is_active',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendance_date', 'employee', 'clock_in_time', 'clock_out_time', 'status')
    list_filter = ('attendance_date', 'status', 'employee__department')
    search_fields = ('employee__staff_no', 'employee__user__first_name', 'employee__user__last_name')
    date_hierarchy = 'attendance_date'
    readonly_fields = ('attendance_date', 'clock_in_time', 'clock_out_time', 'status')

    def has_add_permission(self, request):
        return False


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('official_resumption', 'grace_period_minutes')

    def has_add_permission(self, request):
        return not SystemSetting.objects.exists()


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
