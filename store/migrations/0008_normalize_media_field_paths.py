from django.db import migrations


def strip_media_prefix(apps, schema_editor):
    fields = [
        ('store', 'Product', 'image'),
        ('store', 'HeroCampaign', 'image'),
        ('store', 'Category', 'image'),
    ]
    for app_label, model_name, field_name in fields:
        Model = apps.get_model(app_label, model_name)
        for obj in Model.objects.exclude(**{field_name: ''}):
            value = getattr(obj, field_name)
            if value and str(value).startswith('media/'):
                setattr(obj, field_name, str(value)[len('media/'):])
                obj.save(update_fields=[field_name])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_fix_category_parent_cycles'),
    ]

    operations = [
        migrations.RunPython(strip_media_prefix, noop_reverse),
    ]
