from django.db import models

class Device_Type(models.Model):
    device_type_id = models.BigAutoField(primary_key=True)
    device_type_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.device_type_id)

class Scaling_Value(models.Model):
    scaling_value_id = models.BigAutoField(primary_key=True)
    scaling_value_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.scaling_value_id)
