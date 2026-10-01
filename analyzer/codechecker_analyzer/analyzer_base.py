# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
AnalyzerBase serves as a base-class for analyzer plugins. It describes the
configuration and execution of an analyzer engine.
"""

from abc import ABC, abstractmethod

import importlib
import inspect
from pathlib import Path
import pkgutil
from semver.version import Version

from .plugin_config import AnalyzerConfig, CheckerConfig, PluginConfig

from . import analyzers2

class AnalyzerBase(ABC):
    def __init__(self, config: PluginConfig):
        self.config = config

    def analyze(self):
        ...

    @classmethod
    def is_available(cls) -> bool:
        return cls.get_analyzer_binary() is not None

    @classmethod
    @abstractmethod
    def get_analyzer_config(cls) -> list[AnalyzerConfig]:
        pass

    @classmethod
    @abstractmethod
    def get_checker_config(cls) -> list[CheckerConfig]:
        pass

    @classmethod
    @abstractmethod
    def get_checkers(cls) -> list[str]:
        pass

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_version(cls) -> Version:
        """
        Returns the analyzer's version number. If the version can not be
        fetched from the analyzer tool, then Version(0) returns.
        """
        pass

    @classmethod
    @abstractmethod
    def get_analyzer_binary(cls) -> Path | None:
        pass

    @staticmethod
    def get_analyzers(only_available: bool = False) -> dict[str, type]:
        children = {}

        for module_info in pkgutil.iter_modules(analyzers2.__path__):
            module = importlib.import_module(
                f"{analyzers2.__name__}.{module_info.name}")

            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls is not AnalyzerBase and issubclass(cls, AnalyzerBase) \
                        and (not only_available or cls.is_available()):
                    children[cls.get_name()] = cls

        return children
