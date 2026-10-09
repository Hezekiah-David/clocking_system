from datetime import time

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    ROLE_EMPLOYEE = 'employee'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = ((ROLE_EMPLOYEE, 'Employee / Staff'), (ROLE_ADMIN, 'Administrator'))

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    staff_no = models.CharField(max_length=40, unique=True)
    department = models.CharField(max_length=120)
    designation = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['staff_no']

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.staff_no})'

    def save(self, *args, **kwargs):
        self.user.is_staff = self.role == self.ROLE_ADMIN or self.user.is_superuser
        self.user.save(update_fields=['is_staff'])
        return super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


class Attendance(models.Model):
    STATUS_PRESENT = 'present'
    STATUS_LATE = 'late'
    STATUS_CHOICES = ((STATUS_PRESENT, 'Present'), (STATUS_LATE, 'Late'))

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField(default=timezone.localdate)
    clock_in_time = models.DateTimeField()
    clock_out_time = models.DateTimeField(null=True, blank=True)
    clock_in_face = models.FileField(upload_to='attendance_faces/', blank=True)
    clock_out_face = models.FileField(upload_to='attendance_faces/', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        ordering = ['-attendance_date', '-clock_in_time']
        constraints = [models.UniqueConstraint(fields=['employee', 'attendance_date'], name='one_attendance_per_employee_day')]

    def __str__(self):
        return f'{self.employee.staff_no} - {self.attendance_date}'


class SystemSetting(models.Model):
    official_resumption = models.TimeField(default=time(8, 0))
    grace_period_minutes = models.PositiveIntegerField(default=15)

    class Meta:
        verbose_name = 'Clocking setting'
        verbose_name_plural = 'Clocking settings'

    def __str__(self):
        return 'Clocking rules'

    @classmethod
    def current(cls):
        setting, _ = cls.objects.get_or_create(pk=1)
        return setting
