from django.db import migrations


def fix_self_parent_categories(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    for category in Category.objects.exclude(parent__isnull=True):
        if category.parent_id == category.id:
            category.parent_id = None
            category.save(update_fields=['parent'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_cardinstallmentgroup_categoryinstallmentrule_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_self_parent_categories, noop_reverse),
    ]
