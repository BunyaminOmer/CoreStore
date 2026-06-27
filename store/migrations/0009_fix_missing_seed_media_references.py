from django.db import migrations


def fix_missing_seed_media(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    HeroCampaign = apps.get_model('store', 'HeroCampaign')

    Product.objects.filter(image='products/s25ultra_e0sjtz').update(image='products/iphone17.jpg')
    HeroCampaign.objects.filter(image='campaigns/Siyah_E-_ticaret_-_LOGO_meiumk').update(image='')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_normalize_media_field_paths'),
    ]

    operations = [
        migrations.RunPython(fix_missing_seed_media, noop_reverse),
    ]
