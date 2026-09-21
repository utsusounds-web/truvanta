"""The double-entry engine. `post_entry` is the single way anything in
the app writes to the ledger — it's where the "books must always
balance" rule is actually enforced (a ValueError, not a silent
adjustment, if the lines you pass don't sum to zero). Every other app
(sales, expenses, suppliers, ...) calls this after its own action
completes; the ledger never invents business logic of its own, it
just records what already happened.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Account, JournalEntry, JournalLine

# (code, name, type) — a standard small-business chart of accounts.
# Codes are stable identifiers other code refers to (see constants
# below) — never renumber an existing code, only add new ones.
DEFAULT_ACCOUNTS = [
    ("1000", "Cash", "asset"),
    ("1010", "Bank", "asset"),
    ("1100", "Accounts Receivable (Customer Credit)", "asset"),
    ("1200", "Inventory", "asset"),
    ("1300", "Equipment & Fixed Assets", "asset"),
    ("2000", "Accounts Payable (Supplier Credit)", "liability"),
    ("2100", "Tax Payable", "liability"),
    ("2200", "Loans Payable", "liability"),
    ("3000", "Owner's Equity", "equity"),
    ("3100", "Owner's Drawings", "equity"),
    ("4000", "Sales Revenue", "income"),
    ("5000", "Cost of Goods Sold", "expense"),
    ("5100", "Operating Expenses", "expense"),
    ("5200", "Inventory Write-offs (Damage/Expiry)", "expense"),
]

# Extra accounts seeded on top of the universal base above, based on
# the business's chosen type at signup — additive only. These live in
# a separate 6000+ code range specifically so they can never collide
# with (or need to renumber) the stable codes above, which apps/sales,
# apps/expenses, and apps/suppliers already import by name (CASH,
# COGS, etc.) and post to directly. Nothing outside this file
# references a 6000+ code, so adding/changing entries here is always
# safe — no other module needs updating when this list changes.
BUSINESS_TYPE_EXTRA_ACCOUNTS = {
    "pharmacy": [
        ("6000", "Expired / Recalled Stock Write-off", "expense"),
    ],
    "restaurant": [
        ("6010", "Food & Ingredient Waste", "expense"),
    ],
    "wholesale": [
        ("6020", "Bulk / Volume Discounts Given", "income"),
    ],
    "supermarket": [
        ("6030", "Shrinkage (Theft/Loss)", "expense"),
    ],
}

# Stable shorthands so calling code never hardcodes a raw string code.
CASH = "1000"
BANK = "1010"
ACCOUNTS_RECEIVABLE = "1100"
INVENTORY = "1200"
FIXED_ASSETS = "1300"
ACCOUNTS_PAYABLE = "2000"
TAX_PAYABLE = "2100"
LOANS_PAYABLE = "2200"
OWNERS_EQUITY = "3000"
OWNERS_DRAWINGS = "3100"
SALES_REVENUE = "4000"
COGS = "5000"
OPERATING_EXPENSES = "5100"
INVENTORY_WRITE_OFFS = "5200"


def ensure_chart_of_accounts(business) -> dict:
    """Seeds the standard accounts for a business the first time
    they're needed — lazy, so existing businesses need no migration
    step — plus a small set of extra accounts specific to the
    business's type (see BUSINESS_TYPE_EXTRA_ACCOUNTS), if any exist
    for it. Returns {code: Account} for convenient lookup."""
    existing = {a.code: a for a in Account.objects.filter(business=business)}
    accounts_to_seed = list(DEFAULT_ACCOUNTS) + list(
        BUSINESS_TYPE_EXTRA_ACCOUNTS.get(business.business_type, [])
    )
    to_create = [
        Account(business=business, code=code, name=name, account_type=account_type)
        for code, name, account_type in accounts_to_seed
        if code not in existing
    ]
    if to_create:
        Account.objects.bulk_create(to_create)
        existing = {a.code: a for a in Account.objects.filter(business=business)}
    return existing


@transaction.atomic
def post_entry(*, business, description, lines, branch=None, entry_date=None,
               source_type="", source_id="", created_by=None):
    """Post a balanced journal entry.

    `lines`: list of (account_code, debit, credit) tuples — exactly
    one of debit/credit non-zero per line. Raises ValueError if the
    lines don't balance (total debits != total credits) or if any
    line tries to be both a debit and a credit — this is what makes
    an unbalanced entry impossible, not just discouraged.
    """
    accounts = ensure_chart_of_accounts(business)
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for code, debit, credit in lines:
        debit = Decimal(str(debit))
        credit = Decimal(str(credit))
        if debit and credit:
            raise ValueError(f"Line for account {code} cannot be both a debit and a credit.")
        if code not in accounts:
            raise ValueError(f"Unknown ledger account code: {code}")
        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise ValueError(
            f"Journal entry does not balance: debits={total_debit}, credits={total_credit}. "
            f"This entry was NOT posted."
        )
    if total_debit == 0:
        raise ValueError("A journal entry must have at least one non-zero line.")

    entry = JournalEntry.objects.create(
        business=business, branch=branch, entry_date=entry_date or timezone.now(),
        description=description, source_type=source_type, source_id=str(source_id),
        created_by=created_by,
    )
    JournalLine.objects.bulk_create([
        JournalLine(journal_entry=entry, account=accounts[code], debit=Decimal(str(d)), credit=Decimal(str(c)))
        for code, d, c in lines
    ])
    return entry


def reverse_entry(*, original: JournalEntry, description=None, created_by=None):
    """The only sanctioned way to 'undo' a posted entry — creates a
    new entry with every debit/credit swapped, linked back to the
    original. The original is never touched. Net effect on every
    account: zero, but the history of both the mistake and its
    correction stays visible forever."""
    lines = [(line.account.code, line.credit, line.debit) for line in original.lines.all()]
    entry = post_entry(
        business=original.business, branch=original.branch,
        description=description or f"Reversal of: {original.description}",
        lines=lines, source_type=original.source_type, source_id=original.source_id,
        created_by=created_by,
    )
    entry.reverses = original
    entry.save(update_fields=["reverses"])
    return entry


def record_opening_balance(*, business, user, as_of_date, cash_on_hand=0, bank_balance=0,
                            accounts_receivable=0, inventory_value=0, fixed_assets=0,
                            accounts_payable=0, loans_payable=0):
    """Records (or corrects) a business's starting financial position
    as one balanced opening journal entry, plus a row remembering the
    human-entered breakdown for redisplay/PDF purposes.

    Correcting an existing statement reverses its old journal entry
    first (the standard, only sanctioned way to undo a posted entry —
    see reverse_entry) rather than editing it in place, so the ledger
    stays an honest history of what was recorded and when, not just a
    snapshot of the latest guess.
    """
    from .models import OpeningBalanceStatement

    amounts = {
        "cash_on_hand": Decimal(str(cash_on_hand)), "bank_balance": Decimal(str(bank_balance)),
        "accounts_receivable": Decimal(str(accounts_receivable)), "inventory_value": Decimal(str(inventory_value)),
        "fixed_assets": Decimal(str(fixed_assets)), "accounts_payable": Decimal(str(accounts_payable)),
        "loans_payable": Decimal(str(loans_payable)),
    }
    total_assets = amounts["cash_on_hand"] + amounts["bank_balance"] + amounts["accounts_receivable"] + amounts["inventory_value"] + amounts["fixed_assets"]
    total_liabilities = amounts["accounts_payable"] + amounts["loans_payable"]
    net_worth = total_assets - total_liabilities

    existing = OpeningBalanceStatement.objects.filter(business=business).first()
    if existing and existing.journal_entry:
        reverse_entry(
            original=existing.journal_entry,
            description=f"Correcting opening balance for {business.name}",
            created_by=user,
        )

    lines = []
    if amounts["cash_on_hand"]:
        lines.append((CASH, amounts["cash_on_hand"], 0))
    if amounts["bank_balance"]:
        lines.append((BANK, amounts["bank_balance"], 0))
    if amounts["accounts_receivable"]:
        lines.append((ACCOUNTS_RECEIVABLE, amounts["accounts_receivable"], 0))
    if amounts["inventory_value"]:
        lines.append((INVENTORY, amounts["inventory_value"], 0))
    if amounts["fixed_assets"]:
        lines.append((FIXED_ASSETS, amounts["fixed_assets"], 0))
    if amounts["accounts_payable"]:
        lines.append((ACCOUNTS_PAYABLE, 0, amounts["accounts_payable"]))
    if amounts["loans_payable"]:
        lines.append((LOANS_PAYABLE, 0, amounts["loans_payable"]))
    # Owner's Equity is always the balancing figure — what's left over
    # once everything owed is subtracted from everything owned. A
    # negative net worth (owes more than they own) is entered as a
    # debit to Equity instead of a credit — still balances, and is
    # exactly what a negative starting position means in double-entry
    # terms: the owner starts the books already "owing" the business.
    if net_worth >= 0:
        lines.append((OWNERS_EQUITY, 0, net_worth))
    else:
        lines.append((OWNERS_EQUITY, -net_worth, 0))

    entry = post_entry(
        business=business, description="Opening balance",
        lines=lines, entry_date=timezone.now(), source_type="opening_balance",
        source_id=str(business.id), created_by=user,
    )

    statement, _ = OpeningBalanceStatement.objects.update_or_create(
        business=business,
        defaults={**amounts, "as_of_date": as_of_date, "journal_entry": entry, "recorded_by": user},
    )
    return statement


def account_balance(account: Account) -> Decimal:
    """Signed balance in the account's own normal-balance direction —
    positive means 'more of what this account normally holds'."""
    totals = account.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
    debit = totals["debit"] or Decimal("0")
    credit = totals["credit"] or Decimal("0")
    return debit - credit if account.normal_balance == "debit" else credit - debit


def trial_balance(business) -> list:
    """The classic report: every account and its balance, for
    checking the whole ledger actually balances (sum of every
    account's raw debit total should equal the sum of every credit
    total, business-wide)."""
    accounts = Account.objects.filter(business=business, is_active=True).prefetch_related("lines")
    return [
        {"code": a.code, "name": a.name, "type": a.account_type, "balance": str(account_balance(a))}
        for a in accounts
    ]
