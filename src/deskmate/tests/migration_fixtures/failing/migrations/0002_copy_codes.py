from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("migfix_fail", "0001_kept"),
    ]

    operations = [
        migrations.RunSQL(
            [
                "CREATE TABLE migfix_fail_partial (code text PRIMARY KEY)",
                "INSERT INTO migfix_fail_partial (code) "
                "SELECT code FROM migfix_fail_source",
            ]
        ),
    ]
