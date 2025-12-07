import os
from django.db import models
from .datasets import Datasets
from .users import Users
import uuid

def archive_path(instance, filename):
    dataset_name = instance.dataset_id.dataset_name
    return os.path.join(
        dataset_name,
        'Archives',
        filename
    )

class BaseTransfer(models.Model):
    transfer_id = models.BigAutoField(primary_key=True)
    dataset_id = models.ForeignKey(Datasets, on_delete=models.CASCADE, db_column='dataset_id')
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    total_files_expected = models.PositiveIntegerField(default=0)
    progress = models.PositiveSmallIntegerField(default=0)
    files_uploaded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

    
class UploadTransfer(BaseTransfer):
    def __str__(self):
        return f"progress {self.progress}"

class DownloadDataset(BaseTransfer):
    PHASE_CHOICES = [
        ('preparing', 'Preparing Files'),
        ('zipping', 'Creating Archive'),
        ('ready', 'Ready for Download'),
        ('copying', 'Copying Dataset')
    ]
    
    phase = models.CharField(
        max_length=20,
        choices=PHASE_CHOICES,
        default='preparing'
    )
    archive_file = models.FileField(
        upload_to='dataset_archives/',
        null=True,
        blank=True
    )
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Download {self.transfer_id} - {self.dataset_id.dataset_name}"

    @property
    def download_url(self):
        if self.archive_file:
            return self.archive_file.url
        return None

    def delete_archive_file(self):
        """Удаляет физический файл архива"""
        if self.archive_file:
            if os.path.isfile(self.archive_file.path):
                os.remove(self.archive_file.path)
            self.archive_file.delete(save=False)