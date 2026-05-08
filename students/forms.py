import csv
import io
from django import forms
from .models import Student

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Select CSV File', help_text='Must be .csv format')
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV.")
        return file

class StudentPhotoForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['photo']
        widgets = {'photo': forms.ClearableFileInput(attrs={'accept': 'image/*'})}
