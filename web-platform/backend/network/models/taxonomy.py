from django.db import models

class Species(models.Model):
    species_id = models.BigAutoField(primary_key=True)
    species_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.species_id)

class Sex(models.Model):
    sex_id = models.BigAutoField(primary_key=True)
    sex_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.sex_id)

class Object_Metadata(models.Model):
    object_metadata_id = models.BigAutoField(primary_key=True)
    species_id = models.ForeignKey(Species, on_delete=models.SET_NULL, db_column='species_id', null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    sex_id = models.ForeignKey(Sex, on_delete=models.SET_NULL, db_column='sex_id', null=True, blank=True)

    def __str__(self):
        return str(self.object_metadata_id)
