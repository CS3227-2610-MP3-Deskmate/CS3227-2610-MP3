from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("migfix_gate", "0002_wait"),
    ]

    operations = [
        migrations.RunSQL("CREATE TABLE migfix_gate_after (id integer)"),
    ]
