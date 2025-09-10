from django.db import models

class ProcessedPhone(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'processed_phones'

    def __str__(self):
        return self.phone_number