# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
import multiprocessing
import sys
from typing import Dict, List, Optional, Tuple

from codechecker_common.skiplist_handler import SkipListHandlers
from codechecker_report_converter.util import load_json_or_empty


class AnalysisConfig:
    def __init__(self):
        # Paths to compilation database JSON files.
        #
        # TODO: Do we need to store these file names? The compile commands
        # come from compilation database JSON files basically, however some
        # test codes provide compile commands directly. If JSON file paths are
        # not used anywhere then we could get rid of them in this object.
        # It also wouldn't be good if self.compilation_databases and
        # self.compile_commands don't belong to each other.
        self.compilation_databases: List[str] = []

        self.plugin_options: Dict = {}

        self.skip_handlers: SkipListHandlers = SkipListHandlers()

        # See compile_commands() function.
        self.__compile_commands: List = []

        # TODO: pathlib.Path()
        self.output_dir: str = ''

        # Number of parallel jobs allowed.
        self.jobs: int = multiprocessing.cpu_count()

        # Don't print stdout and stderr outputs of the analyzer tool.
        self.quiet: bool = False

        # The plugin should capture and save the analyzer tool's standard
        # output even in case of successful analysis.
        self.capture_analysis_output: bool = False

        # The plugin should generate a "reproducer" directory which contains
        # everything that makes the analysis reproducible in a portable way.
        self.generate_reproducer: bool = False

        # Analysis should timeout after this many seconds. 0 seconds means no
        # timeout.
        self.timeout: int = 0

        # Specifies the algorithm for report hash generation.
        # TODO: What does None mean? What is the default?
        # TODO: Should be Optional[HashType].
        self.report_hash_type: Optional[str] = None

        # List of enabled and disabled checkers. This is a list of pairs: the
        # parameter of --enable or --disable flag and a bool indicating whether
        # it was given through --enable.
        self.checker_enabling: List[Tuple[str, bool]] = []

        # The analyzer plugin should enable all reasonable checkers (some debug
        # or alpha state checkers may still remain excluded).
        self.enable_all: bool = False

        # TODO: These will be passed as plugin_options to the specific
        # analyzers. The problem now is that ClangSA and clang-tidy are
        # currently handled as one plugin.
        self.analyzer_config: List[str] = []
        self.checker_config: List[str] = []

    @property
    def compile_commands(self) -> List[Dict]:
        """
        self.compilation_databases contains a list of compilation database JSON
        files. In case of a big project these files may be too big and reading
        them is a costly operation. This function is parsing these JSON files
        and storing them in a cache object so the next time the list of build
        actions can be returned immediately.

        TODO: It's too drastic to give sys.exit(1) here.

        TODO: Currently the lists of compiler actions are concatenated from all
        compilation databases. In the future maybe the compilation databases
        will belong to a specific analyzer.
        """
        if not self.__compile_commands:
            for compilation_database in self.compilation_databases:
                x = load_json_or_empty(compilation_database)

                if x is None:
                    sys.exit(1)

                self.__compile_commands.extend(x)

        return self.__compile_commands

    @compile_commands.setter
    def compile_commands(self, values):
        self.__compile_commands = values
