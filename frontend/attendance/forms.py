from django import forms
from django.core.exceptions import ValidationError
from .models import Student, CameraStream
# from PIL import Image
# import face_recognition


class StudentForm(forms.ModelForm):
    """Form for adding/editing students."""
    
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'email', 'phone_number', 'branch', 'year', 'section', 'placement_status', 'assessment_status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.Select(attrs={'class': 'form-control'}),
            'section': forms.Select(attrs={'class': 'form-control'}),
            'placement_status': forms.Select(attrs={'class': 'form-control'}),
            'assessment_status': forms.Select(attrs={'class': 'form-control'}),
        }


class AttendanceFilterForm(forms.Form):
    """Form for filtering attendance records."""
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.filter(is_active=True),
        required=False,
        empty_label="All Students",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + [('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class CameraStreamForm(forms.ModelForm):
    """Form for managing camera streams."""
    
    class Meta:
        model = CameraStream
        fields = ['name', 'rtsp_url', 'http_url', 'is_active', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'rtsp_url': forms.URLInput(attrs={'class': 'form-control'}),
            'http_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
