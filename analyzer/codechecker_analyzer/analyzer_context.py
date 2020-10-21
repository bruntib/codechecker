# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Context to store package related information.
"""


# pylint: disable=no-name-in-module
from distutils.spawn import find_executable

import os
import sys

from codechecker_common import config_maps
from codechecker_common import logger
from codechecker_common.util import load_json_or_empty

from . import env

LOG = logger.get_logger('system')


# -----------------------------------------------------------------------------
class Context(object):
    """ Generic package specific context. """

    def __init__(self, package_root, pckg_layout, cfg_dict):
        env_vars = cfg_dict['environment_variables']

        # Get the common environment variables.
        self.pckg_layout = pckg_layout
        self.env_vars = env_vars

        self._package_root = package_root
        self._severity_map = config_maps.SeverityMap(
            load_json_or_empty(self.checker_severity_map_file, {}))
        self._guideline_map = config_maps.GuidelineMap(
            self.checker_guideline_map_file)
        self._profile_map = config_maps.ProfileMap(
            self.checker_profile_map_file)
        self.__package_version = None
        self.__package_build_date = None
        self.__package_git_hash = None
        self.__analyzers = {}

        self.logger_bin = None
        self.logger_file = None
        self.logger_compilers = None

        # Get package specific environment variables.
        self.set_env(env_vars)

        self.__set_version()
        self.__populate_analyzers()
        self.__populate_replacer()

    def set_env(self, env_vars):
        """
        Get the environment variables.
        """
        # Get generic package specific environment variables.
        self.logger_bin = os.environ.get(env_vars['cc_logger_bin'])
        self.logger_file = os.environ.get(env_vars['cc_logger_file'])
        self.logger_compilers = os.environ.get(env_vars['cc_logger_compiles'])
        self.ld_preload = os.environ.get(env_vars['ld_preload'])
        self.ld_lib_path = env_vars['env_ld_lib_path']

    def __set_version(self):
        """
        Get the package version from the version config file.
        """
        vfile_data = load_json_or_empty(self.version_file)

        if not vfile_data:
            sys.exit(1)

        package_version = vfile_data['version']
        package_build_date = vfile_data['package_build_date']
        package_git_hash = vfile_data.get('git_hash')
        package_git_tag = vfile_data.get('git_describe', {}).get('tag')
        package_git_dirtytag = vfile_data.get('git_describe', {}).get('dirty')

        self.__package_version = package_version['major'] + '.' + \
            package_version['minor'] + '.' + \
            package_version['revision']

        self.__package_build_date = package_build_date
        self.__package_git_hash = package_git_hash

        self.__package_git_tag = package_git_tag
        if (LOG.getEffectiveLevel() == logger.DEBUG or
                LOG.getEffectiveLevel() ==
                logger.DEBUG_ANALYZER):
            self.__package_git_tag = package_git_dirtytag

    def __populate_analyzers(self):
        """ Set analyzer binaries for each registered analyzers. """
        analyzer_env = None
        analyzer_from_path = env.is_analyzer_from_path()
        if not analyzer_from_path:
            analyzer_env = env.extend(self.path_env_extra,
                                      self.ld_lib_path_extra)

        compiler_binaries = self.pckg_layout.get('analyzers')
        for name, value in compiler_binaries.items():

            if analyzer_from_path:
                value = os.path.basename(value)

            if os.path.dirname(value):
                # Check if it is a package relative path.
                self.__analyzers[name] = os.path.join(self._package_root,
                                                      value)
            else:
                env_path = analyzer_env['PATH'] if analyzer_env else None
                compiler_binary = find_executable(value, env_path)
                if not compiler_binary:
                    LOG.warning("'%s' binary can not be found in your PATH!",
                                value)
                    continue

                self.__analyzers[name] = os.path.realpath(compiler_binary)

    def __populate_replacer(self):
        """ Set clang-apply-replacements tool. """
        replacer_binary = self.pckg_layout.get('clang-apply-replacements')

        if os.path.dirname(replacer_binary):
            # Check if it is a package relative path.
            self.__replacer = os.path.join(self._package_root, replacer_binary)
        else:
            self.__replacer = find_executable(replacer_binary)

    @property
    def version(self):
        return self.__package_version

    @property
    def package_build_date(self):
        return self.__package_build_date

    @property
    def package_git_hash(self):
        return self.__package_git_hash

    @property
    def package_git_tag(self):
        return self.__package_git_tag

    @property
    def version_file(self):
        return os.path.join(self._package_root, 'config',
                            'analyzer_version.json')

    @property
    def env_var_cc_logger_bin(self):
        return self.env_vars['cc_logger_bin']

    @property
    def env_var_ld_preload(self):
        return self.env_vars['ld_preload']

    @property
    def env_var_cc_logger_file(self):
        return self.env_vars['cc_logger_file']

    @property
    def path_logger_bin(self):
        return os.path.join(self.package_root, 'bin', 'ld_logger')

    @property
    def path_logger_lib(self):
        return os.path.join(self.package_root, 'ld_logger', 'lib')

    @property
    def logger_lib_name(self):
        return 'ldlogger.so'

    @property
    def path_plist_to_html_dist(self):
        return os.path.join(self.package_root, 'lib', 'python3',
                            'plist_to_html', 'static')

    @property
    def path_env_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_paths = self.pckg_layout.get('path_env_extra', [])
        paths = []
        for path in extra_paths:
            paths.append(os.path.join(self._package_root, path))
        return paths

    @property
    def ld_lib_path_extra(self):
        if env.is_analyzer_from_path():
            return []

        extra_lib = self.pckg_layout.get('ld_lib_path_extra', [])
        ld_paths = []
        for path in extra_lib:
            ld_paths.append(os.path.join(self._package_root, path))
        return ld_paths

    @property
    def analyzer_binaries(self):
        return self.__analyzers

    @property
    def replacer_binary(self):
        return self.__replacer

    @property
    def package_root(self):
        return self._package_root

    @property
    def checker_plugin(self):
        # Do not load the plugin because it might be incompatible.
        if env.is_analyzer_from_path():
            return None

        return os.path.join(self._package_root, 'plugin')

    @property
    def checker_severity_map_file(self):
        """
        Returns the path of checker-severity mapping config file. This file
        may come from a custom location provided by CC_SEVERITY_MAP_FILE
        environment variable.
        """
        # Get severity map file from the environment.
        severity_map_file = os.environ.get('CC_SEVERITY_MAP_FILE')
        if severity_map_file:
            LOG.warning("Severity map file set through the "
                        "'CC_SEVERITY_MAP_FILE' environment variable: %s",
                        severity_map_file)

            return severity_map_file

        return os.path.join(self._package_root, 'config',
                            'checker_severity_map.json')

    @property
    def checker_guideline_map_file(self):
        """
        Returns the path of checker-guideline mapping config file. This file
        may come from a custom location provided by CC_GUIDELINE_MAP_FILE
        environment variable.
        """
        # Get coding guideline map file from the environment.
        guideline_map_file = os.environ.get('CC_GUIDELINE_MAP_FILE')
        if guideline_map_file:
            LOG.warning("Coding guideline map file set through the "
                        "'CC_GUIDELINE_MAP_FILE' environment variable: %s",
                        guideline_map_file)

            return guideline_map_file

        return os.path.join(self._package_root, 'config',
                            'checker_guideline_map.json')

    @property
    def checker_profile_map_file(self):
        """
        Returns the path of checker-profile mapping config file. This file
        may come from a custom location provided by CC_PROFILE_MAP_FILE
        environment variable.
        """
        # Get profile map file from the environment.
        profile_map_file = os.environ.get('CC_PROFILE_MAP_FILE')
        if profile_map_file:
            LOG.warning("Profile map file set through the "
                        "'CC_PROFILE_MAP_FILE' environment variable: %s",
                        profile_map_file)

            return profile_map_file

        return os.path.join(self._package_root, 'config',
                            'checker_profile_map.json')

    @property
    def severity_map(self):
        return self._severity_map

    @property
    def guideline_map(self):
        return self._guideline_map

    @property
    def profile_map(self):
        return self._profile_map


def get_context():
    LOG.debug('Loading package config.')

    package_root = os.environ['CC_PACKAGE_ROOT']

    pckg_config_file = os.path.join(package_root, "config", "config.json")
    LOG.debug('Reading config: %s', pckg_config_file)
    cfg_dict = load_json_or_empty(pckg_config_file)

    if not cfg_dict:
        sys.exit(1)

    LOG.debug(cfg_dict)

    LOG.debug('Loading layout config.')

    layout_cfg_file = os.path.join(package_root, "config",
                                   "package_layout.json")
    LOG.debug(layout_cfg_file)
    lcfg_dict = load_json_or_empty(layout_cfg_file)

    if not lcfg_dict:
        sys.exit(1)

    try:
        return Context(package_root, lcfg_dict['runtime'], cfg_dict)
    except KeyError:
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except ValueError as err:
        LOG.error(err)
        sys.exit(1)
