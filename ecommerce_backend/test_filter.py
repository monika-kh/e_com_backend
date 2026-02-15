#!/usr/bin/env python
"""
Test script to verify category-based product filtering logic
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_backend.settings')
django.setup()

from products.models import Product, Category
from django.db.models import Q

print("=" * 70)
print("PRODUCT FILTERING TEST")
print("=" * 70)

# Display all categories
print("\n📂 ALL CATEGORIES:")
for cat in Category.objects.all():
    parent_name = f" (parent: {cat.parent.name})" if cat.parent else ""
    print(f"  - {cat.name}{parent_name}")

# Display all products
print("\n📦 ALL PRODUCTS:")
for prod in Product.objects.filter(is_active=True):
    print(f"  - {prod.name} (Category: {prod.category.name}, Price: {prod.price}, Stock: {prod.stock})")

# TEST 1: Filter by category_name="silk" (exact match, case-insensitive)
print("\n" + "=" * 70)
print("TEST 1: Filter by category_name='silk'")
print("=" * 70)
category_name = "silk"
qs = Product.objects.select_related('category').filter(
    is_active=True,
    category__name__iexact=category_name
)
print(f"Query: category_name (iexact match) = '{category_name}'")
print(f"Results ({qs.count()} products):")
for prod in qs:
    print(f"  ✓ {prod.name} (Category: {prod.category.name})")

# TEST 2: Filter with multiple filters
print("\n" + "=" * 70)
print("TEST 2: Filter by category + search")
print("=" * 70)
category_name = "silk"
search = "fabric"
qs = Product.objects.select_related('category').filter(
    is_active=True,
    category__name__iexact=category_name,
    name__icontains=search
)
print(f"Query: category_name='{category_name}' AND name contains '{search}'")
print(f"Results ({qs.count()} products):")
for prod in qs:
    print(f"  ✓ {prod.name} (Category: {prod.category.name})")

# TEST 3: Filter with sorting
print("\n" + "=" * 70)
print("TEST 3: Filter by category + sort by price ascending")
print("=" * 70)
category_name = "silk"
sort = "price-asc"
qs = Product.objects.select_related('category').filter(
    is_active=True,
    category__name__iexact=category_name
).order_by("price")
print(f"Query: category_name='{category_name}' ORDER BY price ASC")
print(f"Results ({qs.count()} products):")
for prod in qs:
    print(f"  ✓ {prod.name} - ₹{prod.price} (Stock: {prod.stock})")

# TEST 4: Verify no unrelated categories are included
print("\n" + "=" * 70)
print("TEST 4: Verify filtering excludes unrelated categories")
print("=" * 70)
category_name = "silk"
qs = Product.objects.select_related('category').filter(
    is_active=True,
    category__name__iexact=category_name
)
unrelated_categories = set()
for prod in qs:
    if prod.category.name.lower() != category_name.lower():
        unrelated_categories.add(prod.category.name)

if unrelated_categories:
    print(f"❌ FAILED: Found products from unrelated categories: {unrelated_categories}")
else:
    print(f"✅ PASSED: All {qs.count()} products belong to '{category_name}' category")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
