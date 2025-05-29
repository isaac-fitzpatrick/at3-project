from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)  # Safely create the profile without duplicating

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):  # Ensure profile exists before trying to save
        instance.profile.save()

def validate_unique_nickname(nickname, instance=None):
    if instance:
        # Exclude the current instance from the uniqueness check
        if Profile.objects.filter(nickname=nickname).exclude(pk=instance.pk).exists():
            raise ValidationError(f"Nickname '{nickname}' is already taken.")
    else:
        if Profile.objects.filter(nickname=nickname).exists():
            raise ValidationError(f"Nickname '{nickname}' is already taken.")

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30)
    surname = models.CharField(max_length=30)
    nickname = models.CharField(max_length=30, unique=True, null=False, blank=False)
    max_spend = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)  # max spend
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)  # users balance
    is_teacher = models.BooleanField(default=False) # users permissions (teacher/student)
    pfp = models.FileField(default='pfps/blank.jpg') # profile picture field

    def clean(self):
        validate_unique_nickname(self.nickname, instance=self)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)    

    def __str__(self):
        return self.user.username
    
    @property
    def pfp_url(self):
        filename = f"{self.nickname}.jpg"
        file_path = os.path.join(settings.MEDIA_ROOT, "pfps", filename)
        print("Checking for profile image at:", file_path)
        if os.path.exists(file_path):
            return f"{settings.MEDIA_URL}pfps/{filename}"
        else:
            return f"{settings.MEDIA_URL}pfps/blank.jpg"

class Transaction():
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(user, amount):
        cleaned_data = super().save(user, amount)

class Files():
    def uploadfile(path, file, name):
        os.rename(f'{file}', f'{name}')
        file_path = os.path.join(path, name)
        file.save(path)
        return