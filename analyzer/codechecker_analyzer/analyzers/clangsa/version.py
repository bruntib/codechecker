# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Parse the 'clang --version' command output."""

import os
import re
import shutil
import subprocess

from codechecker_analyzer import analyzer_context


class ClangVersionInfo:
    """ClangVersionInfo holds the version information of the used Clang."""

    def __init__(self,
                 major_version=None,
                 minor_version=None,
                 patch_version=None,
                 installed_dir=None,
                 vendor=None):

        self.major_version = int(major_version)
        self.minor_version = int(minor_version)
        self.patch_version = int(patch_version)
        self.installed_dir = str(installed_dir)
        self.vendor = str(vendor)


class ClangVersionInfoParser:
    """
    ClangVersionInfoParser is responsible for creating ClangVersionInfo
    instances from the version output of Clang.
    """

    def __init__(self, analyzer_binary='clang'):
        self.analyzer_binary = analyzer_binary
        self.clang_version_pattern = (
            r"(?P<vendor>clang|Apple LLVM) version (?P<major_version>[0-9]+)"
            r"\.(?P<minor_version>[0-9]+)\.(?P<patch_version>[0-9]+)")

        self.clang_installed_dir_pattern =\
            r"InstalledDir: (?P<installed_dir>[^\s]*)"

    def parse(self, version_string):
        """Try to parse the version string using the predefined patterns."""
        version_match = re.search(self.clang_version_pattern, version_string)
        if not version_match:
            return

        installed_dir_match = re.search(
            self.clang_installed_dir_pattern, version_string)

        if installed_dir_match:
            installed_dir = installed_dir_match.group('installed_dir')
        else:
            installed_dir = os.path.dirname(shutil.which(self.analyzer_binary))

        return ClangVersionInfo(
            version_match.group('major_version'),
            version_match.group('minor_version'),
            version_match.group('patch_version'),
            installed_dir,
            version_match.group('vendor'))


def get(clang_binary):
    """Get and parse the version information from given clang binary

    Should return False for getting the version
    information not from a clang compiler.
    """
    # TODO: Based on the function parameter the caller may assume that this
    # function returns the version of any Clang binary. PATH and
    # LD_LIBRARY_PATH environment variables are extended in
    # Context.analyzer_env only if CC_ANALYZERS_FROM_PATH is not set, so this
    # function works as expected even if Clang comes from the user's PATH. This
    # environment was implicitly set even before this commit, when it came as
    # a function parameter. But even then analyzer_env was given every time
    # when this function was called.
    compiler_version = subprocess.check_output(
        [clang_binary, '--version'],
        env=analyzer_context.get_context().analyzer_env,
        encoding="utf-8",
        errors="ignore")
    version_parser = ClangVersionInfoParser(clang_binary)
    version_info = version_parser.parse(compiler_version)
    return version_info
