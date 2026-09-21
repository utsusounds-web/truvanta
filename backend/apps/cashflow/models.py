from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TenantScopedModel


class RecurringExpenseSchedule(TenantScopedModel):
    """A known, recurring obligation the owner has told the system
    about — rent, salaries, a loan repayment, a subscription — used
    to power the Cash-Flow Danger-Day Forecast (differentiator
    feature).

    Deliberately NOT inferred automatically from historical Expense
    records: pattern-guessing from a small business's noisy,
    irregular expense history would produce a 'prediction' dressed up
    as fact, which is exactly what this project's rules warn against
    (never invent numbers; say insufficient data instead). The owner
    already knows their rent is due on the 1st — this just asks them
    once and does the arithmetic from there.
    """
    name = models.CharField(max_length=200, help_text="e.g. 'Shop rent', 'Staff salaries'")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    day_of_month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day of the month this is due. For months shorter than this, treated as due on the last day.",
    )
    category = models.ForeignKey(
        "expenses.ExpenseCategory", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Optional — for context only, doesn't post an actual Expense record.",
    )
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.CASCADE, null=True, blank=True,
        help_text="Leave blank if this applies business-wide rather than to one branch.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_month", "name"]

    def __str__(self):
        return f"{self.name} — {self.amount} on day {self.day_of_month}"
