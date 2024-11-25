#!/usr/bin/env python

import os
import sys

from django.core.management import execute_from_command_line


def main():
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.config.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
