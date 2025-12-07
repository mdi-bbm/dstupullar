from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver


class Users(AbstractUser):
    user_id = models.BigAutoField(primary_key=True)
    last_name = None
    first_name = None
    last_login = None
    date_joined = None
    id = None
    groups = None
    user_permissions = None

    def __str__(self):
        return self.username

class Color(models.Model):
    color = models.CharField(max_length=7)
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True)

    def __str__(self):
        return self.color

class Status(models.Model):
    user_id = models.OneToOneField(
        Users,
        on_delete=models.CASCADE,
        db_column='user_id'
    )
    status = models.CharField(max_length=50, default='FREE')

    def __str__(self):
        return f"Status: {self.status}"

@receiver(post_save, sender=Users)
def create_user_status(sender, instance, created, **kwargs):
    if created:
        Status.objects.create(user_id=instance)

class UserPreferences(models.Model):
    from .datasets import Datasets
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    preferences = models.JSONField()
    dataset_id = models.ForeignKey(Datasets, on_delete=models.CASCADE, db_column='dataset_id', null=True, blank=True)

    def __str__(self):
        return f"Preferences for {self.user_id}"
    
 