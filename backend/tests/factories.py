from decimal import Decimal
import uuid

from apps.accounts.models import User, Role, Membership
from apps.tenants.models import Business, Branch
from apps.products.models import Product, UnitOfMeasure


def make_user(email="owner@example.com", password="StrongPass123!"):
    return User.objects.create_user(username=email, email=email, password=password)


def make_business_with_owner(user, name="Test Shop"):
    business = Business.objects.create(
        name=name, slug=name.lower().replace(" ", "-"), owner=user,
        signup_code=uuid.uuid4().hex[:8].upper(),
    )
    role = Role.objects.create(business=business, name="Owner", system_role="owner")
    Membership.objects.create(user=user, business=business, role=role)
    branch = Branch.objects.create(business=business, name="Main Branch")
    return business, branch


def make_product(business, name="Rice 5kg", cost=Decimal("2000"), price=Decimal("2500"), reorder_level=5):
    unit, _ = UnitOfMeasure.objects.get_or_create(business=business, name="Piece", abbreviation="pc")
    product = Product.objects.create(
        business=business, name=name, sku=name[:10], base_unit=unit,
        cost_price=cost, selling_price=price, reorder_level=reorder_level,
    )
    return product, unit
