from django.db import models
from .roles import Groups

class Access_Types(models.Model):
    access_type_id = models.BigAutoField(primary_key=True)
    access_type_name = models.CharField(max_length=255)

    def __str__(self):
        return str(self.access_type_id)

class Access_Policies(models.Model):
    access_policy_id = models.BigAutoField(primary_key=True)
    access_type_id = models.ForeignKey(Access_Types, on_delete=models.CASCADE, db_column='access_type_id')

    def __str__(self):
        return str(self.access_policy_id)

class Access_Group_Linkage(models.Model):
    group_id = models.ForeignKey(Groups, on_delete=models.CASCADE, db_column='group_id')
    access_policy_id = models.ForeignKey(Access_Policies, on_delete=models.CASCADE, db_column='access_policy_id')

    def __str__(self):
        return str(self.group_id)
