# Generated manually to fix duplicate CartItem issue

from django.db import migrations, models


def merge_duplicate_cart_items(apps, schema_editor):
    """
    Merge duplicate CartItems: if multiple items exist for same cart+product,
    sum their quantities into the first one and delete the rest.
    """
    CartItem = apps.get_model('cart', 'CartItem')
    
    # Find all cart+product combinations that have duplicates
    from django.db.models import Count
    duplicates = CartItem.objects.values('cart', 'product').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    for dup in duplicates:
        # Get all duplicate items for this cart+product combination
        items = CartItem.objects.filter(
            cart_id=dup['cart'],
            product_id=dup['product']
        ).order_by('id')
        
        if items.count() > 1:
            # Keep the first one, merge quantities from others
            first_item = items.first()
            total_quantity = sum(item.quantity for item in items)
            first_item.quantity = total_quantity
            first_item.save()
            
            # Delete the rest
            items.exclude(id=first_item.id).delete()


def reverse_merge(apps, schema_editor):
    """Reverse migration - nothing to do as we can't recreate duplicates"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0001_initial'),
    ]

    operations = [
        # Step 1: Merge any existing duplicates
        migrations.RunPython(merge_duplicate_cart_items, reverse_merge),
        
        # Step 2: Add unique constraint
        migrations.AlterUniqueTogether(
            name='cartitem',
            unique_together={('cart', 'product')},
        ),
    ]
