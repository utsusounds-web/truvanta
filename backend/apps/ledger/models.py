import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Account(models.Model):
    """One line in a business's Chart of Accounts. Standard accounting
    types — everything the app posts to the ledger (see services.py)
    resolves to one of these by `code`, which is stable and never
    reused, so historical journal entries always point somewhere real.

    Seeded automatically per business the first time it's needed (see
    services.ensure_chart_of_accounts) — no manual setup required.
    """

    TYPE_CHOICES = [
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="accounts")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("business", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def normal_balance(self) -> str:
        """Which side (debit/credit) increases this account — the
        standard accounting convention, used to compute a signed
        balance from raw debit/credit totals."""
        return "debit" if self.account_type in ("asset", "expense") else "credit"


class JournalEntry(models.Model):
    """One balanced transaction — a group of JournalLines whose debits
    equal its credits exactly (enforced in services.post_entry, never
    at the database level alone, since Postgres/SQLite can't express
    'these related rows must sum to zero' as a constraint).

    Never edited or deleted once posted — see services.reverse_entry
    for how a mistake gets corrected: a new, opposite entry, with both
    pointing at each other. This is what makes the ledger an audit
    trail instead of just a snapshot.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("tenants.Business", on_delete=models.CASCADE, related_name="journal_entries")
    branch = models.ForeignKey("tenants.Branch", on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_entries")
    entry_date = models.DateTimeField()
    description = models.CharField(max_length=255)

    # What in the app caused this entry — a Sale, Expense, etc. Lets
    # you trace "why does this account have this balance" back to a
    # real business action, matching the drill-down requirement.
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=64, blank=True)

    reverses = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reversed_by")

    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        indexes = [models.Index(fields=["business", "source_type", "source_id"])]

    def __str__(self):
        return f"{self.entry_date:%Y-%m-%d} — {self.description}"


class OpeningBalanceStatement(models.Model):
    """A business's financial starting point, captured once (and
    correctable) when they begin using Truvanta with an already-
    running business — as opposed to starting fresh with nothing yet.
    Without this, every calculation (net worth, business health,
    profit-since-inception) would silently assume the business began
    at zero, which is simply false for anyone who already has stock,
    customers who owe them, or their own debts to a supplier.

    Posts as a real, balanced opening journal entry (see
    services.record_opening_balance) so the ledger, not just this
    row, reflects the true starting position — this table exists
    mainly to remember the human-entered breakdown for redisplay and
    the PDF statement, not as a second source of truth."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField("tenants.Business", on_delete=models.CASCADE, related_name="opening_balance")

    as_of_date = models.DateField(help_text="The date this snapshot represents — usually 'today', but can be backdated to when the business actually started using Truvanta.")

    cash_on_hand = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bank_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    accounts_receivable = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Total money customers currently owe you.")
    inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="What your current stock is worth at cost.")
    fixed_assets = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Equipment, furniture, fittings — things you own that aren't for resale.")
    accounts_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Total you currently owe suppliers.")
    loans_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Outstanding loans or other debts.")

    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_assets(self):
        return self.cash_on_hand + self.bank_balance + self.accounts_receivable + self.inventory_value + self.fixed_assets

    @property
    def total_liabilities(self):
        return self.accounts_payable + self.loans_payable

    @property
    def net_worth(self):
        return self.total_assets - self.total_liabilities

    def __str__(self):
        return f"{self.business.name} opening balance as of {self.as_of_date}"


class JournalLine(models.Model):
    """One debit or credit within a JournalEntry. Exactly one of
    debit/credit is non-zero per line — a line is never both."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["id"]

    def __str__(self):
        side = f"Dr {self.debit}" if self.debit else f"Cr {self.credit}"
        return f"{self.account.code}: {side}"
