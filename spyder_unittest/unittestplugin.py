# -*- coding: utf-8 -*-
#
# Copyright © 2013 Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)
"""Unit testing Plugin."""

# Third party imports
from qtpy.QtWidgets import QVBoxLayout
from spyder.config.base import get_translation
from spyder.plugins import SpyderPluginWidget
from spyder.py3compat import getcwd
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.widgets.projects.config import ProjectConfig

# Local imports
from spyder_unittest.widgets.configdialog import Config
from spyder_unittest.widgets.unittestgui import UnitTestWidget

_ = get_translation("unittest", dirname="spyder_unittest")


class UnitTestPlugin(SpyderPluginWidget):
    """Spyder plugin for unit testing."""

    CONF_SECTION = 'unittest'
    CONF_DEFAULTS = [(CONF_SECTION, {'framework': '', 'wdir': ''})]
    CONF_VERSION = '0.1.0'

    def __init__(self, parent):
        """
        Initialize plugin and corresponding widget.

        The part of the initialization that depends on `parent` is done in
        `self.register_plugin()`.
        """
        SpyderPluginWidget.__init__(self, parent)
        self.main = parent  # Spyder 3 compatibility

        # Create unit test widget. For compatibility with Spyder 3.x
        # here we check if the plugin has the attributes
        # 'options_button' and 'options_menu'. See issue 83
        if hasattr(self, 'options_button') and hasattr(self, 'options_menu'):
            # Works with Spyder 4.x
            self.unittestwidget = UnitTestWidget(
                self.main,
                options_button=self.options_button,
                options_menu=self.options_menu)
        else:
            # Works with Spyder 3.x
            self.unittestwidget = UnitTestWidget(self.main)

        # Add unit test widget in dockwindow
        layout = QVBoxLayout()
        layout.addWidget(self.unittestwidget)
        self.setLayout(layout)

        # Initialize plugin
        self.initialize_plugin()

    def update_pythonpath(self):
        """
        Update Python path used to run unit tests.

        This function is called whenever the Python path set in Spyder changes.
        It synchronizes the Python path in the unittest widget with the Python
        path in Spyder.
        """
        self.unittestwidget.pythonpath = self.main.get_spyder_pythonpath()

    def handle_project_change(self):
        """
        Handle the event where the current project changes.

        This updates the default working directory for running tests and loads
        the test configuration from the project preferences.
        """
        self.update_default_wdir()
        self.load_config()

    def update_default_wdir(self):
        """
        Update default working dir for running unit tests.

        The default working dir for running unit tests is set to the project
        directory if a project is open, or the current working directory if no
        project is opened. This function is called whenever this directory may
        change.
        """
        wdir = self.main.projects.get_active_project_path()
        if not wdir:  # if no project opened
            wdir = getcwd()
        self.unittestwidget.default_wdir = wdir

    def load_config(self):
        """
        Load test configuration from project preferences.

        If the test configuration stored in the project preferences is valid,
        then use it. If it is not valid (e.g., because the user never
        configured testing for this project) or no project is opened, then
        invalidate the current test configuration.
        """
        project = self.main.projects.get_active_project()
        if not project:
            self.unittestwidget.set_config_without_emit(None)
            return

        try:
            project_conf = project.CONF[self.CONF_SECTION]
        except KeyError:
            project_conf = ProjectConfig(
                name=self.CONF_SECTION,
                root_path=project.root_path,
                filename=self.CONF_SECTION + '.ini',
                defaults=self.CONF_DEFAULTS,
                load=True,
                version=self.CONF_VERSION)
            project.CONF[self.CONF_SECTION] = project_conf

        new_config = Config(
            framework=project_conf.get(self.CONF_SECTION, 'framework'),
            wdir=project_conf.get(self.CONF_SECTION, 'wdir'))
        if not self.unittestwidget.config_is_valid(new_config):
            new_config = None
        self.unittestwidget.set_config_without_emit(new_config)

    def save_config(self, test_config):
        """
        Save test configuration in project preferences.

        If no project is opened, then do not save.
        """
        project = self.main.projects.get_active_project()
        if not project:
            return
        project_conf = project.CONF[self.CONF_SECTION]
        project_conf.set(self.CONF_SECTION, 'framework', test_config.framework)
        project_conf.set(self.CONF_SECTION, 'wdir', test_config.wdir)

    def goto_in_editor(self, filename, lineno):
        """
        Go to specified line in editor.

        This function is called when the unittest widget emits `sig_edit_goto`.
        Note that the line number in the signal is zero based (the first line
        is line 0), but the editor expects a one-based line number.
        """
        self.main.editor.load(filename, lineno + 1, '')

# ----- SpyderPluginWidget API --------------------------------------------

    def get_plugin_title(self):
        """Return widget title."""
        return _("Unit testing")

    def get_plugin_icon(self):
        """Return widget icon."""
        return ima.icon('profiler')

    def get_focus_widget(self):
        """Return the widget to give focus to this dockwidget when raised."""
        return self.unittestwidget.testdataview

    def get_plugin_actions(self):
        """Return a list of actions related to plugin."""
        return self.unittestwidget.create_actions()

    def on_first_registration(self):
        """Action to be performed on first plugin registration."""
        self.main.tabify_plugins(self.main.help, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window."""
        # Get information from Spyder proper into plugin
        self.update_pythonpath()
        self.update_default_wdir()

        # Connect to relevant signals
        self.main.sig_pythonpath_changed.connect(self.update_pythonpath)
        self.main.workingdirectory.set_explorer_cwd.connect(
            self.update_default_wdir)
        self.main.projects.sig_project_created.connect(
            self.handle_project_change)
        self.main.projects.sig_project_loaded.connect(
            self.handle_project_change)
        self.main.projects.sig_project_closed.connect(
            self.handle_project_change)
        self.unittestwidget.sig_newconfig.connect(self.save_config)
        self.unittestwidget.sig_edit_goto.connect(self.goto_in_editor)

        # Add plugin as dockwidget to main window
        self.main.add_dockwidget(self)

        # Create action and add it to Spyder's menu
        unittesting_act = create_action(
            self,
            _("Run unit tests"),
            icon=ima.icon('profiler'),
            shortcut="Shift+Alt+F11",
            triggered=self.maybe_configure_and_start)
        self.main.run_menu_actions += [unittesting_act]
        self.main.editor.pythonfile_dependent_actions += [unittesting_act]

        # Save all files before running tests
        self.unittestwidget.pre_test_hook = self.main.editor.save_all

    def refresh_plugin(self):
        """Refresh unit testing widget."""
        # For compatibility with Spyder 3.x here we check if the plugin
        # has the attributes 'options_button' and 'options_menu'. See issue 83
        if hasattr(self, 'options_button') and hasattr(self, 'options_menu'):
            self.options_menu.clear()
            self.get_plugin_actions()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed."""
        return True

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings."""
        pass

    # ----- Public API --------------------------------------------------------
    def maybe_configure_and_start(self):
        """
        Ask for configuration if necessary and then run tests.

        Raise unittest widget. If the current test configuration is
        not valid (or not set), then ask the user to configure. Then
        run the tests.
        """
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        self.unittestwidget.maybe_configure_and_start()
