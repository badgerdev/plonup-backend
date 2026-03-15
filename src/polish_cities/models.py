from django.db import models


class PolishCity(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    lat = models.FloatField()
    lng = models.FloatField()
    feature_code = models.CharField(max_length=10, default="PPL")
    population = models.IntegerField(null=True, default=None)
    admin1 = models.CharField(max_length=100, blank=True, db_index=True)
    postal_code = models.CharField(max_length=10, blank=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "lat", "lng"], name="unique_city_coords"),
        ]

    def __str__(self):
        return self.name
