# bottle_preferences.py
#
# Copyright 2022 brombinmirko <send@mirko.pm>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import re
import contextlib
from gettext import gettext as _
from gi.repository import Gtk, Adw

from bottles.frontend.utils.threading import RunAsync  # pyright: reportMissingImports=false
from bottles.frontend.utils.gtk import GtkUtils

from bottles.backend.runner import Runner, gamemode_available, gamescope_available, mangohud_available, \
    obs_vkc_available, vkbasalt_available, vmtouch_available
from bottles.backend.managers.runtime import RuntimeManager
from bottles.backend.utils.manager import ManagerUtils

from bottles.backend.models.result import Result

from bottles.frontend.windows.filechooser import FileChooser
from bottles.frontend.windows.envvars import EnvVarsDialog
from bottles.frontend.windows.drives import DrivesDialog
from bottles.frontend.windows.dlloverrides import DLLOverridesDialog
from bottles.frontend.windows.gamescope import GamescopeDialog
from bottles.frontend.windows.vkbasalt import VkBasaltDialog
from bottles.frontend.windows.display import DisplayDialog
from bottles.frontend.windows.sandbox import SandboxDialog
from bottles.frontend.windows.protonalert import ProtonAlertDialog
from bottles.frontend.windows.exclusionpatterns import ExclusionPatternsDialog
from bottles.frontend.windows.vmtouch import VmtouchDialog

from bottles.backend.wine.catalogs import win_versions
from bottles.backend.wine.reg import Reg
from bottles.backend.wine.regkeys import RegKeys
from bottles.backend.utils.gpu import GPUUtils


# noinspection PyUnusedLocal
@Gtk.Template(resource_path='/com/usebottles/bottles/details-preferences.ui')
class PreferencesView(Adw.PreferencesPage):
    __gtype_name__ = 'DetailsPreferences'

    # region Widgets
    btn_manage_components = Gtk.Template.Child()
    btn_manage_gamescope = Gtk.Template.Child()
    btn_manage_vkbasalt = Gtk.Template.Child()
    btn_manage_display = Gtk.Template.Child()
    btn_manage_sandbox = Gtk.Template.Child()
    btn_manage_versioning_patterns = Gtk.Template.Child()
    btn_manage_vmtouch = Gtk.Template.Child()
    btn_cwd = Gtk.Template.Child()
    btn_cwd_reset = Gtk.Template.Child()
    row_dxvk = Gtk.Template.Child()
    row_vkd3d = Gtk.Template.Child()
    row_nvapi = Gtk.Template.Child()
    row_latencyflex = Gtk.Template.Child()
    row_discrete = Gtk.Template.Child()
    row_vkbasalt = Gtk.Template.Child()
    row_runtime = Gtk.Template.Child()
    row_steam_runtime = Gtk.Template.Child()
    row_cwd = Gtk.Template.Child()
    row_env_variables = Gtk.Template.Child()
    row_overrides = Gtk.Template.Child()
    row_drives = Gtk.Template.Child()
    row_sandbox = Gtk.Template.Child()
    entry_name = Gtk.Template.Child()
    switch_dxvk = Gtk.Template.Child()
    switch_mangohud = Gtk.Template.Child()
    switch_obsvkc = Gtk.Template.Child()
    switch_vkbasalt = Gtk.Template.Child()
    switch_vkd3d = Gtk.Template.Child()
    switch_nvapi = Gtk.Template.Child()
    switch_latencyflex = Gtk.Template.Child()
    switch_gamemode = Gtk.Template.Child()
    switch_gamescope = Gtk.Template.Child()
    switch_fsr = Gtk.Template.Child()
    switch_discrete = Gtk.Template.Child()
    switch_pulse_latency = Gtk.Template.Child()
    switch_fixme = Gtk.Template.Child()
    switch_runtime = Gtk.Template.Child()
    switch_steam_runtime = Gtk.Template.Child()
    switch_sandbox = Gtk.Template.Child()
    switch_versioning_compression = Gtk.Template.Child()
    switch_auto_versioning = Gtk.Template.Child()
    switch_versioning_patterns = Gtk.Template.Child()
    switch_vmtouch = Gtk.Template.Child()
    toggle_sync = Gtk.Template.Child()
    toggle_esync = Gtk.Template.Child()
    toggle_fsync = Gtk.Template.Child()
    toggle_futex2 = Gtk.Template.Child()
    combo_fsr = Gtk.Template.Child()
    combo_runner = Gtk.Template.Child()
    combo_dxvk = Gtk.Template.Child()
    combo_vkd3d = Gtk.Template.Child()
    combo_nvapi = Gtk.Template.Child()
    combo_latencyflex = Gtk.Template.Child()
    combo_windows = Gtk.Template.Child()
    combo_language = Gtk.Template.Child()
    spinner_dxvk = Gtk.Template.Child()
    spinner_dxvkbool = Gtk.Template.Child()
    spinner_vkd3d = Gtk.Template.Child()
    spinner_vkd3dbool = Gtk.Template.Child()
    spinner_nvapi = Gtk.Template.Child()
    spinner_nvapibool = Gtk.Template.Child()
    spinner_latencyflex = Gtk.Template.Child()
    spinner_latencyflexbool = Gtk.Template.Child()
    spinner_runner = Gtk.Template.Child()
    spinner_windows = Gtk.Template.Child()
    spinner_display = Gtk.Template.Child()
    box_sync = Gtk.Template.Child()
    group_details = Gtk.Template.Child()
    exp_components = Gtk.Template.Child()
    str_list_languages = Gtk.Template.Child()
    str_list_runner = Gtk.Template.Child()
    str_list_dxvk = Gtk.Template.Child()
    str_list_vkd3d = Gtk.Template.Child()
    str_list_nvapi = Gtk.Template.Child()
    str_list_latencyflex = Gtk.Template.Child()
    str_list_windows = Gtk.Template.Child()
    ev_controller = Gtk.EventControllerKey.new()

    # endregion

    def __init__(self, details, config, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = details.window
        self.manager = details.window.manager
        self.config = config
        self.queue = details.queue
        self.details = details

        self.entry_name.add_controller(self.ev_controller)

        gpu = GPUUtils().get_gpu()

        # region signals
        self.row_overrides.connect("activated", self.__show_dll_overrides_view)
        self.row_env_variables.connect("activated", self.__show_environment_variables)
        self.row_drives.connect("activated", self.__show_drives)
        self.btn_manage_components.connect("clicked", self.window.show_prefs_view)
        self.btn_manage_gamescope.connect("clicked", self.__show_gamescope_settings)
        self.btn_manage_vkbasalt.connect("clicked", self.__show_vkbasalt_settings)
        self.btn_manage_display.connect("clicked", self.__show_display_settings)
        self.btn_manage_sandbox.connect("clicked", self.__show_sandbox_settings)
        self.btn_manage_versioning_patterns.connect("clicked", self.__show_exclusionpatterns_settings)
        self.btn_manage_vmtouch.connect("clicked", self.__show_vmtouch_settings)
        self.btn_cwd.connect("clicked", self.choose_cwd)
        self.btn_cwd_reset.connect("clicked", self.choose_cwd, True)
        self.toggle_sync.connect('toggled', self.__set_wine_sync)
        self.toggle_esync.connect('toggled', self.__set_esync)
        self.toggle_fsync.connect('toggled', self.__set_fsync)
        self.toggle_futex2.connect('toggled', self.__set_futex2)
        self.switch_dxvk.connect('state-set', self.__toggle_dxvk)
        self.switch_mangohud.connect('state-set', self.__toggle_mangohud)
        self.switch_obsvkc.connect('state-set', self.__toggle_obsvkc)
        self.switch_vkbasalt.connect('state-set', self.__toggle_vkbasalt)
        self.switch_vkd3d.connect('state-set', self.__toggle_vkd3d)
        self.switch_nvapi.connect('state-set', self.__toggle_nvapi)
        self.switch_latencyflex.connect('state-set', self.__toggle_latencyflex)
        self.switch_gamemode.connect('state-set', self.__toggle_gamemode)
        self.switch_gamescope.connect('state-set', self.__toggle_gamescope)
        self.switch_sandbox.connect('state-set', self.__toggle_sandbox)
        self.switch_fsr.connect('state-set', self.__toggle_fsr)
        self.switch_discrete.connect('state-set', self.__toggle_discrete_gpu)
        self.switch_pulse_latency.connect('state-set', self.__toggle_pulse_latency)
        self.switch_fixme.connect('state-set', self.__toggle_fixme)
        self.switch_versioning_compression.connect('state-set', self.__toggle_versioning_compression)
        self.switch_auto_versioning.connect('state-set', self.__toggle_auto_versioning)
        self.switch_versioning_patterns.connect('state-set', self.__toggle_versioning_patterns)
        self.switch_vmtouch.connect('state-set', self.__toggle_vmtouch)
        self.combo_fsr.connect('notify::selected', self.__set_fsr_level)
        self.combo_runner.connect('notify::selected', self.__set_runner)
        self.combo_dxvk.connect('notify::selected', self.__set_dxvk)
        self.combo_vkd3d.connect('notify::selected', self.__set_vkd3d)
        self.combo_nvapi.connect('notify::selected', self.__set_nvapi)
        self.combo_latencyflex.connect('notify::selected', self.__set_latencyflex)
        self.combo_windows.connect('notify::selected', self.__set_windows)
        self.combo_language.connect('notify::selected-item', self.__set_language)
        self.ev_controller.connect("key-released", self.__check_entry_name)
        self.entry_name.connect("apply", self.__save_name)
        # endregion

        """Set DXVK_NVAPI related rows to visible when an NVIDIA GPU is detected (invisible by default)"""
        with contextlib.suppress(KeyError):
            vendor = gpu["vendors"]["nvidia"]["vendor"]
            if vendor == "nvidia":
                self.row_nvapi.set_visible(True)
                self.combo_nvapi.set_visible(True)

        """Set Bottles Runtime row to visible when Bottles is not running inside Flatpak"""
        if "FLATPAK_ID" not in os.environ and RuntimeManager.get_runtimes("bottles"):
            self.row_runtime.set_visible(True)
            self.switch_runtime.connect('state-set', self.__toggle_runtime)

        if RuntimeManager.get_runtimes("steam"):
            self.row_steam_runtime.set_visible(True)
            self.switch_steam_runtime.connect('state-set', self.__toggle_steam_runtime)

        '''Toggle some utilities according to its availability'''
        self.switch_gamemode.set_sensitive(gamemode_available)
        self.switch_gamescope.set_sensitive(gamescope_available)
        self.btn_manage_gamescope.set_sensitive(gamescope_available)
        self.switch_vkbasalt.set_sensitive(vkbasalt_available)
        self.btn_manage_vkbasalt.set_sensitive(vkbasalt_available)
        self.switch_mangohud.set_sensitive(mangohud_available)
        self.switch_obsvkc.set_sensitive(obs_vkc_available)
        self.switch_vmtouch.set_sensitive(vmtouch_available)
        _not_available = _("This feature is not available on your system.")
        if not gamemode_available:
            self.switch_gamemode.set_tooltip_text(_not_available)
        if not gamescope_available:
            self.switch_gamescope.set_tooltip_text(_not_available)
            self.btn_manage_gamescope.set_tooltip_text(_not_available)
        if not vkbasalt_available:
            self.switch_vkbasalt.set_tooltip_text(_not_available)
            self.btn_manage_vkbasalt.set_tooltip_text(_not_available)         
        if not mangohud_available:
            self.switch_mangohud.set_tooltip_text(_not_available)
        if not obs_vkc_available:
            self.switch_obsvkc.set_tooltip_text(_not_available)
        if not vmtouch_available:
            self.switch_vmtouch.set_tooltip_text(_not_available)

    def __check_entry_name(self, *_args):
        self.__valid_name = GtkUtils.validate_entry(self.entry_name)

    def __save_name(self, *_args):
        if not self.__valid_name:
            self.entry_name.set_text(self.config.get("Name"))
            self.__valid_name = True
            return

        name = self.entry_name.get_text()
        self.manager.update_config(
            config=self.config,
            key="Name",
            value=name
        )
        self.window.page_list.update_bottles()

    def choose_cwd(self, widget, reset=False):
        """Change the default current working directory for the bottle"""

        def set_path(_dialog, response, _file_dialog):
            if response == Gtk.ResponseType.OK:
                _file = _file_dialog.get_file()
                _path = _file.get_path()
                if _path and _path != "":
                    self.row_cwd.set_subtitle(_path)
                    self.manager.update_config(
                        config=self.config,
                        key="WorkingDir",
                        value=_path
                    )
                    self.btn_cwd_reset.set_visible(True)
                else:
                    self.row_cwd.set_subtitle(_("Default to the bottle path."))
                    self.btn_cwd_reset.set_visible(False)

            _dialog.destroy()

        if not reset:
            FileChooser(
                parent=self.window,
                title=_("Choose working directory for executables"),
                action=Gtk.FileChooserAction.SELECT_FOLDER,
                buttons=(_("Cancel"), _("Select")),
                path=ManagerUtils.get_bottle_path(self.config),
                native=False,
                callback=set_path
            )

        self.manager.update_config(config=self.config, key="WorkingDir", value="")
        self.row_cwd.set_subtitle(_("Default to the bottle path."))
        self.btn_cwd_reset.set_visible(False)

    def update_combo_components(self):
        """
        This function update the components' combo boxes with the
        items in the manager catalogs. It also temporarily disable
        the functions connected to the combo boxes to avoid the
        bottle configuration to be updated during the process.
        """
        self.combo_runner.handler_block_by_func(self.__set_runner)
        self.combo_dxvk.handler_block_by_func(self.__set_dxvk)
        self.combo_vkd3d.handler_block_by_func(self.__set_vkd3d)
        self.combo_nvapi.handler_block_by_func(self.__set_nvapi)
        self.combo_latencyflex.handler_block_by_func(self.__set_latencyflex)
        self.combo_language.handler_block_by_func(self.__set_language)
        self.combo_windows.handler_block_by_func(self.__set_windows)

        self.str_list_runner.splice(0, self.str_list_runner.get_n_items())
        self.str_list_dxvk.splice(0, self.str_list_dxvk.get_n_items())
        self.str_list_vkd3d.splice(0, self.str_list_vkd3d.get_n_items())
        self.str_list_nvapi.splice(0, self.str_list_nvapi.get_n_items())
        self.str_list_latencyflex.splice(0, self.str_list_latencyflex.get_n_items())
        self.str_list_languages.splice(0, self.str_list_languages.get_n_items())
        self.str_list_windows.splice(0, self.str_list_windows.get_n_items())

        for index, dxvk in enumerate(self.manager.dxvk_available):
            self.str_list_dxvk.append(dxvk)

        for index, vkd3d in enumerate(self.manager.vkd3d_available):
            self.str_list_vkd3d.append(vkd3d)

        for index, runner in enumerate(self.manager.runners_available):
            self.str_list_runner.append(runner)

        for index, nvapi in enumerate(self.manager.nvapi_available):
            self.str_list_nvapi.append(nvapi)

        for index, latencyflex in enumerate(self.manager.latencyflex_available):
            self.str_list_latencyflex.append(latencyflex)

        for lang in ManagerUtils.get_languages():
            self.str_list_languages.append(lang)

        self.combo_runner.handler_unblock_by_func(self.__set_runner)
        self.combo_dxvk.handler_unblock_by_func(self.__set_dxvk)
        self.combo_vkd3d.handler_unblock_by_func(self.__set_vkd3d)
        self.combo_nvapi.handler_unblock_by_func(self.__set_nvapi)
        self.combo_latencyflex.handler_unblock_by_func(self.__set_latencyflex)
        self.combo_language.handler_unblock_by_func(self.__set_language)
        self.combo_windows.handler_unblock_by_func(self.__set_windows)

    def set_config(self, config):
        self.config = config
        parameters = self.config.get("Parameters")

        # temporary lock functions connected to the widgets
        self.switch_dxvk.handler_block_by_func(self.__toggle_dxvk)
        self.switch_mangohud.handler_block_by_func(self.__toggle_mangohud)
        self.switch_vkd3d.handler_block_by_func(self.__toggle_vkd3d)
        self.switch_nvapi.handler_block_by_func(self.__toggle_nvapi)
        self.switch_latencyflex.handler_block_by_func(self.__toggle_latencyflex)
        self.switch_vkbasalt.handler_block_by_func(self.__toggle_vkbasalt)
        self.switch_obsvkc.handler_block_by_func(self.__toggle_obsvkc)
        self.switch_gamemode.handler_block_by_func(self.__toggle_gamemode)
        self.switch_gamescope.handler_block_by_func(self.__toggle_gamescope)
        self.switch_sandbox.handler_block_by_func(self.__toggle_sandbox)
        self.switch_discrete.handler_block_by_func(self.__toggle_discrete_gpu)
        self.switch_fsr.handler_block_by_func(self.__toggle_fsr)
        self.switch_pulse_latency.handler_block_by_func(self.__toggle_pulse_latency)
        self.switch_versioning_compression.handler_block_by_func(self.__toggle_versioning_compression)
        self.switch_auto_versioning.handler_block_by_func(self.__toggle_auto_versioning)
        self.switch_versioning_patterns.handler_block_by_func(self.__toggle_versioning_patterns)
        with contextlib.suppress(TypeError):
            self.switch_runtime.handler_block_by_func(self.__toggle_runtime)
            self.switch_steam_runtime.handler_block_by_func(self.__toggle_steam_runtime)
        self.combo_fsr.handler_block_by_func(self.__set_fsr_level)
        self.combo_runner.handler_block_by_func(self.__set_runner)
        self.combo_dxvk.handler_block_by_func(self.__set_dxvk)
        self.combo_vkd3d.handler_block_by_func(self.__set_vkd3d)
        self.combo_nvapi.handler_block_by_func(self.__set_nvapi)
        self.combo_latencyflex.handler_block_by_func(self.__set_latencyflex)
        self.combo_windows.handler_block_by_func(self.__set_windows)
        self.combo_language.handler_block_by_func(self.__set_language)
        self.toggle_sync.handler_block_by_func(self.__set_wine_sync)
        self.toggle_esync.handler_block_by_func(self.__set_esync)
        self.toggle_fsync.handler_block_by_func(self.__set_fsync)
        self.toggle_futex2.handler_block_by_func(self.__set_futex2)
        self.ev_controller.handler_block_by_func(self.__check_entry_name)

        self.switch_dxvk.set_active(parameters["dxvk"])
        self.switch_mangohud.set_active(parameters["mangohud"])
        self.switch_obsvkc.set_active(parameters["obsvkc"])
        self.switch_vkbasalt.set_active(parameters["vkbasalt"])
        self.switch_vkd3d.set_active(parameters["vkd3d"])
        self.switch_nvapi.set_active(parameters["dxvk_nvapi"])
        self.switch_latencyflex.set_active(parameters["latencyflex"])
        self.switch_gamemode.set_active(parameters["gamemode"])
        self.switch_gamescope.set_active(parameters["gamescope"])
        self.switch_sandbox.set_active(parameters["sandbox"])
        self.switch_fsr.set_active(parameters["fsr"])
        self.switch_versioning_compression.set_active(parameters["versioning_compression"])
        self.switch_auto_versioning.set_active(parameters["versioning_automatic"])
        self.switch_versioning_patterns.set_active(parameters["versioning_exclusion_patterns"])
        self.switch_runtime.set_active(parameters["use_runtime"])
        self.switch_steam_runtime.set_active(parameters["use_steam_runtime"])
        self.switch_vmtouch.set_active(parameters["vmtouch"])

        self.toggle_sync.set_active(parameters["sync"] == "wine")
        self.toggle_esync.set_active(parameters["sync"] == "esync")
        self.toggle_fsync.set_active(parameters["sync"] == "fsync")
        self.toggle_futex2.set_active(parameters["sync"] == "futex2")

        self.switch_discrete.set_active(parameters["discrete_gpu"])
        self.switch_pulse_latency.set_active(parameters["pulseaudio_latency"])

        self.btn_cwd_reset.set_visible(self.config.get("WorkingDir"))

        self.entry_name.set_text(config["Name"])

        if self.config.get("WorkingDir") != "":
            self.row_cwd.set_subtitle(self.config.get("WorkingDir"))
        else:
            self.row_cwd.set_subtitle(_("Default to the bottle path."))

        self.combo_language.set_selected(ManagerUtils.get_languages(
            from_locale=self.config.get("Language"),
            get_index=True
        ))

        # NOTE: this should not be here but it's the only way to handle windows
        # versions in the current structure, we will fix this in the future
        # with the new Bottles Backend.
        # region Windows Versions
        self.windows_versions = {
            "win10": "Windows 10",
            "win81": "Windows 8.1",
            "win8": "Windows 8",
            "win7": "Windows 7",
            "win2008r2": "Windows 2008 R2",
            "win2008": "Windows 2008",
            # "vista": "Windows Vista", # TODO: implement this in the backend
            "winxp": "Windows XP"
        }

        if self.config.get("Arch") == "win32":
            self.windows_versions["win98"] = "Windows 98"
            self.windows_versions["win95"] = "Windows 95"

        for index, windows_version in enumerate(self.windows_versions):
            self.str_list_windows.append(self.windows_versions[windows_version])
            if windows_version == self.config.get("Windows"):
                self.combo_windows.set_selected(index)
        # endregion

        _dxvk = self.config.get("DXVK")
        if _dxvk in self.manager.dxvk_available:
            if _i_dxvk := self.manager.dxvk_available.index(_dxvk):
                self.combo_dxvk.set_selected(_i_dxvk)

        _vkd3d = self.config.get("VKD3D")
        if _vkd3d in self.manager.vkd3d_available:
            if _i_vkd3d := self.manager.vkd3d_available.index(_vkd3d):
                self.combo_vkd3d.set_selected(_i_vkd3d)

        _nvapi = self.config.get("DXVK_NVAPI")
        if _nvapi in self.manager.nvapi_available:
            if _i_nvapi := self.manager.nvapi_available.index(_nvapi):
                self.combo_nvapi.set_selected(_i_nvapi)

        _latencyflex = self.config.get("LatencyFlex")
        if _latencyflex in self.manager.latencyflex_available:
            if _i_latencyflex := self.manager.latencyflex_available.index(_latencyflex):
                self.combo_latencyflex.set_selected(_i_latencyflex)

        _runner = self.config.get("Runner")
        if _runner in self.manager.runners_available:
            if _i_runner := self.manager.runners_available.index(_runner):
                self.combo_runner.set_selected(_i_runner)

        # unlock functions connected to the widgets
        self.switch_dxvk.handler_unblock_by_func(self.__toggle_dxvk)
        self.switch_mangohud.handler_unblock_by_func(self.__toggle_mangohud)
        self.switch_vkd3d.handler_unblock_by_func(self.__toggle_vkd3d)
        self.switch_nvapi.handler_unblock_by_func(self.__toggle_nvapi)
        self.switch_latencyflex.handler_unblock_by_func(self.__toggle_latencyflex)
        self.switch_vkbasalt.handler_unblock_by_func(self.__toggle_vkbasalt)
        self.switch_obsvkc.handler_unblock_by_func(self.__toggle_obsvkc)
        self.switch_gamemode.handler_unblock_by_func(self.__toggle_gamemode)
        self.switch_gamescope.handler_unblock_by_func(self.__toggle_gamescope)
        self.switch_sandbox.handler_unblock_by_func(self.__toggle_sandbox)
        self.switch_discrete.handler_unblock_by_func(self.__toggle_discrete_gpu)
        self.switch_fsr.handler_unblock_by_func(self.__toggle_fsr)
        self.switch_pulse_latency.handler_unblock_by_func(self.__toggle_pulse_latency)
        self.switch_versioning_compression.handler_unblock_by_func(self.__toggle_versioning_compression)
        self.switch_auto_versioning.handler_unblock_by_func(self.__toggle_auto_versioning)
        self.switch_versioning_patterns.handler_unblock_by_func(self.__toggle_versioning_patterns)
        with contextlib.suppress(TypeError):
            self.switch_runtime.handler_unblock_by_func(self.__toggle_runtime)
            self.switch_steam_runtime.handler_unblock_by_func(self.__toggle_steam_runtime)
        self.combo_fsr.handler_unblock_by_func(self.__set_fsr_level)
        self.combo_runner.handler_unblock_by_func(self.__set_runner)
        self.combo_dxvk.handler_unblock_by_func(self.__set_dxvk)
        self.combo_vkd3d.handler_unblock_by_func(self.__set_vkd3d)
        self.combo_nvapi.handler_unblock_by_func(self.__set_nvapi)
        self.combo_latencyflex.handler_unblock_by_func(self.__set_latencyflex)
        self.combo_windows.handler_unblock_by_func(self.__set_windows)
        self.combo_language.handler_unblock_by_func(self.__set_language)
        self.toggle_sync.handler_unblock_by_func(self.__set_wine_sync)
        self.toggle_esync.handler_unblock_by_func(self.__set_esync)
        self.toggle_fsync.handler_unblock_by_func(self.__set_fsync)
        self.toggle_futex2.handler_unblock_by_func(self.__set_futex2)
        self.ev_controller.handler_unblock_by_func(self.__check_entry_name)

        self.__set_steam_rules()

    def __show_gamescope_settings(self, widget):
        new_window = GamescopeDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_vkbasalt_settings(self, widget):
        new_window = VkBasaltDialog(
            parent_window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_display_settings(self, widget):
        new_window = DisplayDialog(
            parent_window=self.window,
            config=self.config,
            details=self.details,
            queue=self.queue,
            widget=widget,
            spinner_display=self.spinner_display
        )
        new_window.present()

    def __show_exclusionpatterns_settings(self, widget):
        new_window = ExclusionPatternsDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_sandbox_settings(self, widget):
        new_window = SandboxDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_drives(self, widget):
        new_window = DrivesDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_environment_variables(self, widget=False):
        """Show the environment variables dialog"""
        new_window = EnvVarsDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __show_vmtouch_settings(self, widget):
        new_window = VmtouchDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def __set_sync_type(self, sync):
        """
        Set the sync type (wine, esync, fsync, futext2)
        Don't use this directly, use dedicated wrappers instead (e.g. __set_wine_sync)
        """

        def update(result, error=False):
            self.config = result.data["config"]
            toggles = [
                ("wine", self.toggle_sync, self.__set_wine_sync),
                ("esync", self.toggle_esync, self.__set_esync),
                ("fsync", self.toggle_fsync, self.__set_fsync),
                ("futex2", self.toggle_futex2, self.__set_futex2)
            ]
            for sync_type, toggle, func in toggles:
                toggle.handler_block_by_func(func)
                if sync_type == sync:
                    toggle.set_active(True)
                else:
                    toggle.set_active(False)
                toggle.handler_unblock_by_func(func)
            self.box_sync.set_sensitive(True)
            self.queue.end_task()

        self.queue.add_task()
        self.box_sync.set_sensitive(False)
        RunAsync(
            self.manager.update_config,
            callback=update,
            config=self.config,
            key="sync",
            value=sync,
            scope="Parameters"
        )

    def __set_wine_sync(self, widget):
        self.__set_sync_type("wine")

    def __set_esync(self, widget):
        self.__set_sync_type("esync")

    def __set_fsync(self, widget):
        self.__set_sync_type("fsync")

    def __set_futex2(self, widget):
        self.__set_sync_type("futex2")

    def __toggle_dxvk(self, widget=False, state=False):
        """Install/Uninstall DXVK from the bottle"""
        self.queue.add_task()
        self.set_dxvk_status(pending=True)

        RunAsync(
            task_func=self.manager.install_dll_component,
            callback=self.set_dxvk_status,
            config=self.config,
            component="dxvk",
            remove=not state
        )

        self.config = self.manager.update_config(
            config=self.config,
            key="dxvk",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_mangohud(self, widget, state):
        """Toggle the Mangohud for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="mangohud",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_obsvkc(self, widget, state):
        """Toggle the OBS Vulkan capture for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="obsvkc",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_vkbasalt(self, widget, state):
        """Toggle the vkBasalt for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="vkbasalt",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_vkd3d(self, widget=False, state=False):
        """Install/Uninstall VKD3D from the bottle"""
        self.queue.add_task()
        self.set_vkd3d_status(pending=True)

        RunAsync(
            task_func=self.manager.install_dll_component,
            callback=self.set_vkd3d_status,
            config=self.config,
            component="vkd3d",
            remove=not state
        )

        self.config = self.manager.update_config(
            config=self.config,
            key="vkd3d",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_nvapi(self, widget=False, state=False):
        """Install/Uninstall NVAPI from the bottle"""
        self.queue.add_task()
        self.set_nvapi_status(pending=True)

        RunAsync(
            task_func=self.manager.install_dll_component,
            callback=self.set_nvapi_status,
            config=self.config,
            component="nvapi",
            remove=not state
        )

        self.config = self.manager.update_config(
            config=self.config,
            key="dxvk_nvapi",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_latencyflex(self, widget=False, state=False):
        """Install/Uninstall LatencyFlex from the bottle"""
        self.queue.add_task()
        self.set_latencyflex_status(pending=True)

        RunAsync(
            task_func=self.manager.install_dll_component,
            callback=self.set_latencyflex_status,
            config=self.config,
            component="latencyflex",
            remove=not state
        )

        self.config = self.manager.update_config(
            config=self.config,
            key="latencyflex",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_gamemode(self, widget=False, state=False):
        """Toggle the gamemode for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="gamemode",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_gamescope(self, widget=False, state=False):
        """Toggle the gamescope for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="gamescope",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_sandbox(self, widget=False, state=False):
        """Toggle the sandbox for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="sandbox",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_fsr(self, widget, state):
        """Toggle the FSR for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="fsr",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_runtime(self, widget, state):
        """Toggle the Bottles runtime for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="use_runtime",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_steam_runtime(self, widget, state):
        """Toggle the Steam runtime for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="use_steam_runtime",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_discrete_gpu(self, widget, state):
        """Toggle the discrete GPU for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="discrete_gpu",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_versioning_compression(self, widget, state):
        """Toggle the versioning compression for current bottle"""
        def update():
            self.config = self.manager.update_config(
                config=self.config,
                key="versioning_compression",
                value=state,
                scope="Parameters"
            ).data["config"]

        def handle_response(_widget, response_id):
            if response_id == "ok":
                RunAsync(self.manager.versioning_manager.re_initialize, config=self.config)
            _widget.destroy()

        if self.manager.versioning_manager.is_initialized(self.config):
            dialog = Adw.MessageDialog.new(
                self.window,
                _("Toggling Compression Require Re-Initialization"),
                _("This will kepp all your files but will delete all states. Do you want to continue?"),
            )
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("ok", _("Confirm"))
            dialog.connect("response", handle_response)
            dialog.present()
        else:
            update()
    
    def __toggle_auto_versioning(self, widget, state):
        """Toggle the auto versioning for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="versioning_automatic",
            value=state,
            scope="Parameters"
        ).data["config"]
    
    def __toggle_versioning_patterns(self, widget, state):
        """Toggle the versioning patterns for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="versioning_exclusion_patterns",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_vmtouch(self, widget=False, state=False):
        """Toggle vmtouch for current bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="vmtouch",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __set_fsr_level(self, *_args):
        """Set the FSR level of sharpness (from 0 to 3, where 3 is the default)"""
        level = self.combo_fsr.get_selected()
        self.config = self.manager.update_config(
            config=self.config,
            key="fsr_level",
            value=level,
            scope="Parameters"
        ).data["config"]

    def __set_runner(self, *_args):
        """Set the runner to use for the bottle"""

        def set_widgets_status(status=True):
            for w in [
                self.combo_runner,
                self.switch_dxvk,
                self.switch_nvapi,
                self.switch_vkd3d,
                self.combo_dxvk,
                self.combo_nvapi,
                self.combo_vkd3d
            ]:
                w.set_sensitive(status)
            if status:
                self.spinner_runner.stop()
                self.spinner_runner.set_visible(False)
            else:
                self.spinner_runner.start()
                self.spinner_runner.set_visible(True)

        def update(result, error=False):
            if result:
                if "config" in result.data.keys():
                    self.config = result.data["config"]
                if self.config["Parameters"].get("use_steam_runtime"):
                    self.switch_steam_runtime.handler_block_by_func(self.__toggle_steam_runtime)
                    self.switch_steam_runtime.set_active(True)
                    self.switch_steam_runtime.handler_unblock_by_func(self.__toggle_steam_runtime)
            set_widgets_status(True)
            self.queue.end_task()

        set_widgets_status(False)
        runner = self.manager.runners_available[self.combo_runner.get_selected()]

        def run_task(status=True):
            if not status:
                update(Result(True))
                self.combo_runner.handler_block_by_func(self.__set_runner)
                self.combo_runner.handler_unblock_by_func(self.__set_runner)
                return

            self.queue.add_task()
            RunAsync(
                Runner.runner_update,
                callback=update,
                config=self.config,
                manager=self.manager,
                runner=runner
            )

        if re.search("^(GE-)?Proton", runner):
            dialog = ProtonAlertDialog(self.window, run_task)
            dialog.show()
        else:
            run_task()

    def __dll_component_task_func(self, *args, **kwargs):
        # Remove old version
        self.manager.install_dll_component(config=kwargs["config"], component=kwargs["component"], remove=True)
        # Install new version
        self.manager.install_dll_component(config=kwargs["config"], component=kwargs["component"])
        self.queue.end_task()

    def __set_dxvk(self, *_args):
        """Set the DXVK version to use for the bottle"""
        self.set_dxvk_status(pending=True)
        self.queue.add_task()
        dxvk = self.manager.dxvk_available[self.combo_dxvk.get_selected()]
        self.config = self.manager.update_config(
            config=self.config,
            key="DXVK",
            value=dxvk
        ).data["config"]

        RunAsync(
            task_func=self.__dll_component_task_func,
            callback=self.set_dxvk_status,
            config=self.config,
            component="dxvk"
        )

    def __set_vkd3d(self, *_args):
        """Set the VKD3D version to use for the bottle"""
        self.set_vkd3d_status(pending=True)
        self.queue.add_task()
        vkd3d = self.manager.vkd3d_available[self.combo_vkd3d.get_selected()]
        self.config = self.manager.update_config(
            config=self.config,
            key="VKD3D",
            value=vkd3d
        ).data["config"]

        RunAsync(
            task_func=self.__dll_component_task_func,
            callback=self.set_vkd3d_status,
            config=self.config,
            component="vkd3d"
        )

    def __set_nvapi(self, *_args):
        """Set the NVAPI version to use for the bottle"""
        self.set_nvapi_status(pending=True)
        self.queue.add_task()
        nvapi = self.manager.nvapi_available[self.combo_nvapi.get_selected()]
        self.config = self.manager.update_config(
            config=self.config,
            key="NVAPI",
            value=nvapi
        ).data["config"]

        RunAsync(
            task_func=self.__dll_component_task_func,
            callback=self.set_nvapi_status,
            config=self.config,
            component="nvapi"
        )

    def __set_latencyflex(self, *_args):
        """Set the latency flex value"""
        latencyflex = self.manager.latencyflex_available[self.combo_latencyflex.get_selected()]
        self.queue.add_task()
        self.config = self.manager.update_config(
            config=self.config,
            key="LatencyFleX",
            value=latencyflex
        ).data["config"]

        RunAsync(
            task_func=self.__dll_component_task_func,
            callback=self.set_latencyflex_status,
            config=self.config,
            component="latencyflex"
        )

    def __set_windows(self, *_args):
        """Set the Windows version to use for the bottle"""
        # self.manager.dxvk_available[self.combo_dxvk.get_selected()]
        def update(result, error=False):
            self.spinner_windows.stop()
            self.spinner_windows.set_visible(False)
            self.combo_windows.set_sensitive(True)
            self.queue.end_task()

        self.queue.add_task()
        self.spinner_windows.start()
        self.spinner_windows.set_visible(True)
        self.combo_windows.set_sensitive(False)
        rk = RegKeys(self.config)

        for index, windows_version in enumerate(self.windows_versions):
            if self.combo_windows.get_selected() == index:
                self.config = self.manager.update_config(
                    config=self.config,
                    key="Windows",
                    value=windows_version
                ).data["config"]

                RunAsync(
                    rk.set_windows,
                    callback=update,
                    version=windows_version
                )
                break

    def __set_language(self, *_args):
        """Set the language to use for the bottle"""
        index = self.combo_language.get_selected()
        language = ManagerUtils.get_languages(from_index=index)
        self.config = self.manager.update_config(
            config=self.config,
            key="Language",
            value=language[0],
        ).data["config"]

    def __toggle_pulse_latency(self, widget, state):
        """Set the pulse latency to use for the bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="pulseaudio_latency",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __toggle_fixme(self, widget, state):
        """Set the Wine logging level to use for the bottle"""
        self.config = self.manager.update_config(
            config=self.config,
            key="fixme_logs",
            value=state,
            scope="Parameters"
        ).data["config"]

    def __show_dll_overrides_view(self, widget=False):
        """Show the DLL overrides view"""
        new_window = DLLOverridesDialog(
            window=self.window,
            config=self.config
        )
        new_window.present()

    def set_dxvk_status(self, status=None, error=None, pending=False):
        """Set the dxvk status"""
        self.switch_dxvk.set_sensitive(not pending)
        self.combo_dxvk.set_sensitive(not pending)
        if pending:
            self.spinner_dxvk.start()
            self.spinner_dxvkbool.start()
            self.spinner_dxvk.set_visible(True)
            self.spinner_dxvkbool.set_visible(True)
        else:
            self.spinner_dxvk.stop()
            self.spinner_dxvkbool.stop()
            self.spinner_dxvk.set_visible(False)
            self.spinner_dxvkbool.set_visible(False)
            self.queue.end_task()

    def set_vkd3d_status(self, status=None, error=None, pending=False):
        """Set the vkd3d status"""
        self.switch_vkd3d.set_sensitive(not pending)
        self.combo_vkd3d.set_sensitive(not pending)
        if pending:
            self.spinner_vkd3d.start()
            self.spinner_vkd3dbool.start()
            self.spinner_vkd3d.set_visible(True)
            self.spinner_vkd3dbool.set_visible(True)
        else:
            self.spinner_vkd3d.stop()
            self.spinner_vkd3dbool.stop()
            self.spinner_vkd3d.set_visible(False)
            self.spinner_vkd3dbool.set_visible(False)
            self.queue.end_task()

    def set_nvapi_status(self, status=None, error=None, pending=False):
        """Set the nvapi status"""
        self.switch_nvapi.set_sensitive(not pending)
        self.combo_nvapi.set_sensitive(not pending)
        if pending:
            self.spinner_nvapi.start()
            self.spinner_nvapibool.start()
            self.spinner_nvapi.set_visible(True)
            self.spinner_nvapibool.set_visible(True)
        else:
            self.spinner_nvapi.stop()
            self.spinner_nvapibool.stop()
            self.spinner_nvapi.set_visible(False)
            self.spinner_nvapibool.set_visible(False)
            self.queue.end_task()

    def set_latencyflex_status(self, status=None, error=None, pending=False):
        """Set the latencyflex status"""
        self.switch_latencyflex.set_sensitive(not pending)
        self.combo_latencyflex.set_sensitive(not pending)
        if pending:
            self.spinner_latencyflex.start()
            self.spinner_latencyflexbool.start()
            self.spinner_latencyflex.set_visible(True)
            self.spinner_latencyflexbool.set_visible(True)
        else:
            self.spinner_latencyflex.stop()
            self.spinner_latencyflexbool.stop()
            self.spinner_latencyflex.set_visible(False)
            self.spinner_latencyflexbool.set_visible(False)
            self.queue.end_task()

    def __set_steam_rules(self):
        """Set the Steam Environment specific rules"""
        status = False if self.config.get("Environment") == "Steam" else True

        for w in [
            self.row_discrete,
            self.row_steam_runtime,
            self.row_dxvk,
            self.row_vkd3d,
            self.row_latencyflex,
            self.row_sandbox,
            self.group_details,
            self.exp_components
        ]:
            w.set_visible(status)
            w.set_sensitive(status)

        self.row_sandbox.set_visible(self.window.settings.get_boolean("experiments-sandbox"))
