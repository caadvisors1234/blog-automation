from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0005_blogposttemplate_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blogpost',
            name='tone',
        ),
    ]
