"""The committed migrations make the database the models describe.

Accounts are stored as the data model says (TECHNICAL-SPEC "Data model"), so
a model change without its migration would leave the stored schema behind.
"""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.ac("ACC-1.1")
@pytest.mark.django_db
def test_migrations_match_models_no_changes_detected():
    output = StringIO()
    try:
        call_command(
            "makemigrations", "--check", "--dry-run", stdout=output, stderr=output
        )
    except SystemExit as exit_:
        pytest.fail(
            f"makemigrations exited with {exit_.code}; the models have changes "
            f"that no migration makes:\n{output.getvalue()}"
        )
