from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

auth_user = get_user_model()


class Category(models.Model):
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title}"


class Item(models.Model):
    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=19, decimal_places=4)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    image = models.ImageField(upload_to="item_images/", null=True, blank=True)
    stock_quantity = models.IntegerField(default=1)
    in_stock = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    description = models.TextField(default=_("Long description"), null=True)
    short_description = models.CharField(
        max_length=280, default=_("Short description"), null=True
    )

    @property
    def price_rounded(self):
        return round(self.price, 2)

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("winadmin:view_inventory_item", args=[str(self.pk)])
