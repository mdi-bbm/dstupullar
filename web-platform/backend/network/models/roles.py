from django.db import models
from .users import Users

class Roles(models.Model):
    role_id = models.BigAutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return self.role_name

class Groups(models.Model):
    group_id = models.BigAutoField(primary_key=True)

    def __str__(self):
        return str(self.group_id)

class Group_User_Linkage(models.Model):
    group_id = models.ForeignKey(Groups, on_delete=models.CASCADE, db_column='group_id')
    user_id = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    role_id = models.ForeignKey(Roles, on_delete=models.CASCADE, db_column='role_id')

    def __str__(self):
        return str(self.group_id)
