import apps.messaging.storage
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('chats', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=apps.messaging.storage.attachment_upload_path)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to=apps.messaging.storage.attachment_thumbnail_path)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('duration_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('ready', 'Ready'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('processing_error', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'message_attachments',
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('text', 'Text'), ('image', 'Image'), ('video', 'Video'), ('voice', 'Voice'), ('video_circle', 'Video circle'), ('file', 'File')], default='text', max_length=20)),
                ('text', models.TextField(blank=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chats.chat')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='messaging.message')),
            ],
            options={
                'db_table': 'messages',
                'ordering': ['id'],
            },
        ),
    ]
