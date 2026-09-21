from decimal import Decimal, ROUND_UP

from django.db import transaction

from apps.audit.services import log_action
from apps.notifications.services import notify
from .models import Product, PriceHistory, UnitOfMeasure


DEFAULT_UNITS = [
    ("Piece", "pc"), ("Kilogram", "kg"), ("Litre", "l"), ("Box", "box"), ("Carton", "ctn"),
]


def ensure_default_units(business):
    """Seeds a handful of common units the first time a business's
    unit list is ever looked at — so adding the very first product
    never blocks on 'first go set up a Unit of Measure', a fairly
    technical inventory concept a first-time small-shop owner has no
    reason to already know. Someone selling something these don't fit
    can still add a custom unit; this just removes it as a
    prerequisite for everyone else.
    """
    if UnitOfMeasure.objects.filter(business=business).exists():
        return
    for name, abbr in DEFAULT_UNITS:
        UnitOfMeasure.objects.get_or_create(business=business, name=name, defaults={"abbreviation": abbr})


def stock_deductions_for(product: Product, quantity: Decimal):
    """What actually needs to move in inventory when `quantity` of
    `product` is sold. For an ordinary product (or a variant — a
    variant IS a Product, so this needs no special case for it),
    that's just the product itself. For a bundle, nothing is deducted
    from the bundle's own (untracked) stock — instead each component
    is deducted, scaled by both the bundle quantity sold and how much
    of that component one bundle consumes. Returns a list of
    (product, quantity) pairs ready to hand to record_movement.
    """
    if not product.is_bundle:
        return [(product, quantity)]
    return [
        (item.component, item.quantity * quantity)
        for item in product.bundle_items.select_related("component").all()
    ]


def suggest_rebalanced_price(product: Product, new_cost_price: Decimal) -> Decimal:
    """When the price you buy at changes, keep the same profit margin
    (not the same naira/dollar markup) so the suggestion scales
    correctly whether cost went up or down. Falls back to a 20%
    markup if the product currently has no margin to preserve.
    """
    if product.cost_price > 0 and product.selling_price > product.cost_price:
        current_margin_ratio = (product.selling_price - product.cost_price) / product.selling_price
    else:
        current_margin_ratio = Decimal("0.20")
    if current_margin_ratio >= 1:
        current_margin_ratio = Decimal("0.20")
    suggested = new_cost_price / (1 - current_margin_ratio)
    return suggested.quantize(Decimal("0.01"), rounding=ROUND_UP)


@transaction.atomic
def update_cost_price(*, product: Product, new_cost_price: Decimal, actor,
                       new_selling_price: Decimal | None = None, reason: str = ""):
    """Apply a new cost price (e.g. supplier raised/lowered prices).
    If no explicit new_selling_price is given, keeps the existing
    selling price — the caller (API) is expected to have already
    shown the owner the suggested rebalanced price and let them
    confirm or override it, per the 'system should suggest, not
    silently decide' framing.
    """
    old_cost = product.cost_price
    old_selling = product.selling_price
    product.cost_price = new_cost_price
    if new_selling_price is not None:
        product.selling_price = new_selling_price
    product.save(update_fields=["cost_price", "selling_price", "updated_at"])

    PriceHistory.objects.create(
        business=product.business, product=product,
        old_cost_price=old_cost, new_cost_price=new_cost_price,
        old_selling_price=old_selling, new_selling_price=product.selling_price,
        reason=reason, changed_by=actor,
    )
    log_action(
        business=product.business, actor=actor, action="price_change", target=product,
        previous_value={"cost_price": str(old_cost), "selling_price": str(old_selling)},
        new_value={"cost_price": str(new_cost_price), "selling_price": str(product.selling_price)},
        reason=reason or "Cost price updated.",
    )

    business = product.business
    threshold = business.away_mode_price_change_threshold_percent
    if business.away_mode_enabled and threshold and old_cost > 0:
        change_percent = abs((new_cost_price - old_cost) / old_cost) * 100
        if change_percent > threshold:
            notify(
                business=business, level="critical",
                title=f"Large price change while you're away: {product.name}",
                message=f"Cost price changed by {change_percent:.1f}% ({old_cost} -> {new_cost_price}) — "
                        f"above your {threshold}% away-mode limit.",
                link_path="/products",
            )

    return product
