#!/usr/bin/env python
"""Django's command-line utility for Deskmate's administrative tasks."""

import os
import sys


def main():
    """Run the management command named in the command-line arguments."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskmate.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
