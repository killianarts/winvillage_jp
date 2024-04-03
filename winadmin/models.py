from django.db import models
from django.utils.translation import gettext_lazy as _
from recurrence.fields import RecurrenceField


class SpecialDate(models.Model):
    class Meta:
        verbose_name = _("Special Date")
        verbose_name_plural = _("Special Dates")

    name = models.CharField(max_length=50, verbose_name=_("Name"))
    recurrence = RecurrenceField(verbose_name=_("Recurrences"))

    def __str__(self):
        return self.name
