from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("migfix_gate", "0001_before"),
    ]

    operations = [
        migrations.RunSQL(
            [
                "CREATE TABLE migfix_gate_waited (id integer)",
                # Waits while another session holds a lock on the table.
                "SELECT count(*) FROM migfix_gate_source",
            ]
        ),
    ]
