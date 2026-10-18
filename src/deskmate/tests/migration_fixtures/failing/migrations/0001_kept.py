from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL("CREATE TABLE migfix_fail_kept (code text NOT NULL)"),
    ]
