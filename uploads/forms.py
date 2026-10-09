from django import forms
from django.contrib.auth.models import User

from .models import Employee


class EmployeeAdminForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text='Required when creating a new employee.')
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)

    class Meta:
        model = Employee
        fields = ('username', 'password', 'first_name', 'last_name', 'email', 'staff_no', 'department', 'designation', 'role', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            user = self.instance.user
            self.fields['username'].initial = user.username
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_username(self):
        username = self.cleaned_data['username']
        users = User.objects.filter(username=username)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError('This username is already in use.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.instance.pk and not password:
            raise forms.ValidationError('Enter a password for the new employee.')
        return password

    def save(self, commit=True):
        employee = super().save(commit=False)
        if employee.pk:
            user = employee.user
            user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()
        else:
            user = User(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                email=self.cleaned_data['email'],
            )
            user.set_password(self.cleaned_data['password'])
            user.save()
            employee.user = user
        if commit:
            employee.save()
        return employee


class StaffSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    staff_no = forms.CharField(max_length=40)
    department = forms.CharField(max_length=120)
    designation = forms.CharField(max_length=120)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already in use.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError('Passwords do not match.')
        if Employee.objects.filter(staff_no=cleaned_data.get('staff_no')).exists():
            self.add_error('staff_no', 'This staff number is already registered.')
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
        )
        return Employee.objects.create(
            user=user,
            staff_no=self.cleaned_data['staff_no'],
            department=self.cleaned_data['department'],
            designation=self.cleaned_data['designation'],
            role=Employee.ROLE_EMPLOYEE,
        )
