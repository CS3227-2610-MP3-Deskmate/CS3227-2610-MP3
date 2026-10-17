import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("migfix_alpha", "0001_initial"),
        ("migfix_beta", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="board",
            name="pinned",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="migfix_alpha.card",
            ),
        ),
    ]
