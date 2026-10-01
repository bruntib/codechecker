# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
from pathlib import Path
import re
import shlex
import subprocess

from semver.version import Version

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzer_base import AnalyzerBase
from codechecker_analyzer.plugin_config import AnalyzerConfig, CheckerConfig
from codechecker_common.logger import get_logger

LOG = get_logger('analyzer')


def _clang_command_output(command: list[str]) -> str:
    """
    Runs the given Clang command in its proper environment and returns its
    output as a string.
    Throws an exception if the command cannot be executed as a subprocess.
    """
    return subprocess.check_output(
        command,
        stderr=subprocess.STDOUT,
        env=analyzer_context.get_context().get_env_for_bin(command[0]),
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore")


def _parse_clang_help_page(
    command: list[str],
    start_label: str
) -> list[tuple[str, str]]:
    """
    Parse the clang help page starting from a specific label.
    Returns a list of (flag, description) tuples.
    """
    try:
        help_page = _clang_command_output(command)
    except (subprocess.CalledProcessError, OSError):
        LOG.debug("Failed to run '%s' command!", command)
        return []

    try:
        help_page = help_page[help_page.index(start_label) + len(start_label):]
    except ValueError:
        return []

    # This regex will match lines which contain only a flag or a flag and a
    # description: '  <flag>', '  <flag> <description>'.
    start_new_option_rgx = \
        re.compile(r"^\s{2}(?P<flag>\S+)(\s(?P<desc>[^\n]+))?$")

    # This regex will match lines which contain description for the previous
    # flag: '     <description>'
    prev_help_desc_rgx = \
        re.compile(r"^\s{3,}(?P<desc>[^\n]+)$")

    res = []

    flag = None
    desc = []
    for line in help_page.splitlines():
        m = start_new_option_rgx.match(line)
        if m:
            if flag and desc:
                res.append((flag, ' '.join(desc)))
                flag = None
                desc = []

            flag = m.group("flag")
        else:
            m = prev_help_desc_rgx.match(line)

        if m and m.group("desc"):
            desc.append(m.group("desc").strip())

    if flag and desc:
        res.append((flag, ' '.join(desc)))

    return res


class ClangSA(AnalyzerBase):
    @classmethod
    def get_name(cls):
        return 'clangsa'

    @classmethod
    def get_version(cls) -> Version:
        version = [cls.get_analyzer_binary(), '-dumpversion']
        try:
            env = analyzer_context.get_context() \
                .get_env_for_bin(cls.get_analyzer_binary())

            out = subprocess.check_output(version, env=env, encoding="utf-8")

            return Version.parse(out.strip().removesuffix("git"))
        except (subprocess.CalledProcessError, OSError) as ex:
            LOG.warning(
                "Failed to get analyzer version: %s",
                shlex.join(version))
            LOG.warning(ex)

        return Version(0)

    @classmethod
    def get_checkers(cls, alpha: bool = True, debug: bool = False):
        command = [cls.get_analyzer_binary(), "-cc1"]

        command.extend(cls.__plugin_load_flags())

        command.append("-analyzer-checker-help")

        # TODO: The clang compiler on OSX is a few relases older than the open
        # source # clang release. The new checker help printig flags are not
        # available there yet. If the OSX clang will be updated to based on
        # clang v8 this early return can be removed.
        if cls.get_version() != Version(0):
            try:
                help_page = _clang_command_output([
                    cls.get_analyzer_binary(), "-cc1", "--help"])
            except (subprocess.CalledProcessError, OSError):
                help_page = ""

            if alpha and "-analyzer-checker-help-alpha" in help_page:
                command.append("-analyzer-checker-help-alpha")

            if debug and "-analyzer-checker-help-developer" in help_page:
                command.append("-analyzer-checker-help-developer")

        return _parse_clang_help_page(command, 'CHECKERS:')

    @classmethod
    def get_checker_config(cls) -> list[CheckerConfig]:
        """
        Return the list of checker config options.

        Before clang9 alpha and debug checkers were printed by default. Since
        clang9 there are extra arguments to print the additional checkers.
        """
        command = [cls.get_analyzer_binary(), "-cc1"]

        command.extend(cls.__plugin_load_flags())

        command.append("-analyzer-checker-option-help")

        # TODO: The clang compiler on OSX is a few relases older than the open
        # source # clang release. The new checker help printig flags are not
        # available there yet. If the OSX clang will be updated to based on
        # clang v8 this early return can be removed.
        if cls.get_version() != Version(0):
            try:
                help_page = _clang_command_output([
                    cls.get_analyzer_binary(), "-cc1", "--help"])
            except (subprocess.CalledProcessError, OSError):
                help_page = ""

            if "-analyzer-checker-option-help-alpha" in help_page:
                command.append("-analyzer-checker-option-help-alpha")

            if "-analyzer-checker-option-help-developer" in help_page:
                command.append("-analyzer-checker-option-help-developer")

        result = []

        for cfg, doc in _parse_clang_help_page(command, 'OPTIONS:'):
            checker, opt = cfg.split(':', 1)
            result.append(CheckerConfig(checker, opt, "", doc))

        return result

    @classmethod
    def get_analyzer_config(cls) -> list[AnalyzerConfig]:
        """Return the list of analyzer config options."""
        command = [cls.get_analyzer_binary(), "-cc1"]

        command.extend(cls.__plugin_load_flags())

        command.append("-analyzer-config-help")

        analyzer_config_list: list[AnalyzerConfig] = list(map(
            lambda cfg: AnalyzerConfig(cfg[0], "", cfg[1]),
            _parse_clang_help_page(command, 'OPTIONS:')))

        additional_config_list = [
            AnalyzerConfig(
                'cc-verbatim-args-file',
                '',
                'A file path containing flags that are forwarded verbatim to '
                'the analyzer tool. E.g.: cc-verbatim-args-file=<filepath>')
        ]

        return analyzer_config_list + additional_config_list

    @classmethod
    def get_analyzer_binary(cls) -> Path | None:
        return Path(
            analyzer_context.get_context().analyzer_binaries[cls.get_name()])


    @classmethod
    def __analyzer_plugins(cls) -> list[str]:
        """
        Return the list of .so file paths which contain checker plugins to
        ClangSA.
        """
        context = analyzer_context.get_context()
        plugin_dir = context.checker_plugin
        clangsa_plugin_dir = os.environ.get('CC_CLANGSA_PLUGIN_DIR')

        if context.is_analyzer_from_path:
            if not clangsa_plugin_dir:
                return []

            # If the CC_ANALYZERS_FROM_PATH and CC_CLANGSA_PLUGIN_DIR
            # environment variables are set we will use this value as the
            # plugin directory.
            plugin_dir = clangsa_plugin_dir

        if not plugin_dir or not os.path.exists(plugin_dir):
            return []

        return [os.path.join(plugin_dir, f)
                for f in os.listdir(plugin_dir)
                if os.path.isfile(os.path.join(plugin_dir, f))
                and f.endswith(".so")]

    @classmethod
    def __plugin_load_flags(cls):
        """
        ClangSA can be extended with checker plugins. This function extends a
        clang command with these plugins.
        """
        plugin_flags = []

        for plugin in cls.__analyzer_plugins():
            plugin_flags.extend(["-load", plugin])

        return plugin_flags