from django.db import models

# Create your models here.


class UserData(models.Model):
    user_id = models.UUIDField()
    email = models.TextField()
    password = models.TextField()
    full_name = models.TextField()
    user_level = models.IntegerField()  # 1 -> Pro, 2 -> Pro Plus
    join_epoch_time = models.IntegerField(default=0)  # Epoch Time In Seconds
