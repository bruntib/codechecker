# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Plugin config is represented by a dataclass. It contains all configuration
options that the analyzers (inherited from AnalyzerBase) get from the command
line interface.
"""

from dataclasses import dataclass, field
from pathlib import Path

from codechecker_common.skiplist_handler import SkipListHandlers


@dataclass
class AnalyzerConfig:
    option: str
    value: str
    documentation: str | None


@dataclass
class CheckerConfig:
    checker: str
    option: str
    value: str
    documentation: str | None


@dataclass(init=False)
class PluginConfig:
    """
    This class holds various configs required by an analyzer. Its members are
    initialized from the arguments of "CodeChecker analyze" command.
    """

    analyzer_config: list[AnalyzerConfig] = field(default_factory=list)
    checker_config: list[CheckerConfig] = field(default_factory=list)
    enabled_checkers: list[str] = field(default_factory=list)
    skip_list: SkipListHandlers
    input_path: Path
    workspace: Path
    fixit_dir: Path
    reproducer_dir: Path
    generate_reproducer: bool
