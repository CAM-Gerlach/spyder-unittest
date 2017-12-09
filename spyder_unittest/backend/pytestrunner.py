# -*- coding: utf-8 -*-
#
# Copyright © 2013 Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
"""Support for py.test framework."""

# Standard library imports
import os

# Local imports
from spyder_unittest.backend.runnerbase import RunnerBase


class PyTestRunner(RunnerBase):
    """Class for running tests within py.test framework."""

    module = 'pytest'
    name = 'py.test'

    def create_argument_list(self):
        """Create argument list for testing process."""
        pyfile = os.path.join(os.path.dirname(__file__), 'pytestworker.py')
        return [pyfile, '--junit-xml', self.resultfilename]
