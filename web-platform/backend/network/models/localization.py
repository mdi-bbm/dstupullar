from django.db import models

class Localization(models.Model):
    localization_id = models.BigAutoField(primary_key=True)
    localization_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.localization_id)

class Diagnosis(models.Model):
    diagnosis_id = models.BigAutoField(primary_key=True)
    diagnosis_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.diagnosis_id)
