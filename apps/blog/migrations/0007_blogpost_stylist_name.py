from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0006_remove_blogpost_tone'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogpost',
            name='stylist_name',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                verbose_name='Stylist Name',
                help_text='Human-readable stylist name (scraped from HPB)',
            ),
        ),
    ]

