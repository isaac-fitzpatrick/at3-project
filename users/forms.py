from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from .models import Files

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    surname = forms.CharField(max_length=30, required=True)
    nickname = forms.CharField(max_length=30, required=True)
    pfp = forms.FileField(max_length=800, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'surname', 'nickname', 'pfp']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['surname']  
        user.pfp = self.cleaned_data['pfp']     
        if commit:
            user.save()
            profile = user.profile
            profile.first_name = self.cleaned_data['first_name']
            profile.surname = self.cleaned_data['surname']
            profile.nickname = self.cleaned_data['nickname']
            profile.pfp = self.cleaned_data['pfp']
            directory = 'pfps'
            Files.uploadfile(directory, profile.pfp, profile.nickname)
            profile.save()
        return user
    
class BalanceTopupForm(forms.Form):
    amount = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=5)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class Decision(forms.Form): # gives user the choice between teacher/student login
    choice1 = forms.CharField(widget=forms.HiddenInput(), required=False) 
    choice2 = forms.CharField(widget=forms.HiddenInput(), required=False)

    
            


       
