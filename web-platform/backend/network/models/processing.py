from django.db import models

class Processing_Types(models.Model):
    processing_type_id = models.BigAutoField(primary_key=True)
    processing_type = models.CharField(max_length=255)

    def __str__(self):
        return self.processing_type
