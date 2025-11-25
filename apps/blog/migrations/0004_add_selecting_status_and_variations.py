# Generated manually for selecting status and variations field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_alter_postlog_status'),
    ]

    operations = [
        # Add generated_variations field
        migrations.AddField(
            model_name='blogpost',
            name='generated_variations',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='AI-generated article variations for selection',
                verbose_name='Generated Variations'
            ),
        ),
        # Update STATUS_CHOICES (handled in model, just update status field choices)
        migrations.AlterField(
            model_name='blogpost',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('generating', 'AI Generating'),
                    ('selecting', 'Selecting Article'),
                    ('ready', 'Ready to Publish'),
                    ('publishing', 'Publishing'),
                    ('published', 'Published'),
                    ('failed', 'Failed'),
                ],
                db_index=True,
                default='draft',
                max_length=20,
                verbose_name='Status',
            ),
        ),
        # Allow blank title and content for initial state
        migrations.AlterField(
            model_name='blogpost',
            name='title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Blog title (max 25 characters)',
                max_length=25,
                verbose_name='Title',
            ),
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='content',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Final content with image placeholders',
                verbose_name='Content',
            ),
        ),
    ]

