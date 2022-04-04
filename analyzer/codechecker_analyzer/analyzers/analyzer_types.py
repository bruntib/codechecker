# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""


import sys

from codechecker_common.logger import get_logger

from .clangtidy.analyzer import ClangTidy
from .clangsa.analyzer import ClangSA

LOG = get_logger('analyzer')

supported_analyzers = {ClangSA.ANALYZER_NAME: ClangSA,
                       ClangTidy.ANALYZER_NAME: ClangTidy}


def check_available_analyzers(analyzers, errored):
    """ Handle use case when no analyzer can be found on the user machine. """
    for analyzer_binary, reason in errored:
        LOG.warning("Analyzer '%s' is enabled but CodeChecker is failed to "
                    "execute analysis with it: '%s'. Please check your "
                    "'PATH' environment variable and the "
                    "'config/package_layout.json' file!",
                    analyzer_binary, reason)

    if not analyzers:
        LOG.error(
            "Failed to run command because no analyzers can be found on "
            "your machine!")
        sys.exit(1)


def check_supported_analyzers(analyzers):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.
    TODO: This happens implicitly through check_analyzer_availability()
    function. This will be eliminated in the future.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    enabled_analyzers = set()
    failed_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            failed_analyzers.add(
                (analyzer_name, "Analyzer unsupported by CodeChecker!"))
            continue

        check_result = supported_analyzers[analyzer_name] \
            .check_analyzer_availability()

        if check_result is True:
            enabled_analyzers.add(analyzer_name)
        else:
            failed_analyzers.add((analyzer_name, check_result))

    return enabled_analyzers, failed_analyzers


def construct_analyzer(buildaction,
                       analyzer_config):
    try:
        analyzer_type = buildaction.analyzer_type

        LOG.debug_analyzer('Constructing %s analyzer.', analyzer_type)
        if analyzer_type in supported_analyzers:
            analyzer = supported_analyzers[analyzer_type](analyzer_config,
                                                          buildaction)
        else:
            analyzer = None
            LOG.error('Unsupported analyzer type: %s', analyzer_type)
        return analyzer

    except Exception as ex:
        LOG.debug_analyzer(ex)
        return None


def build_config_handlers(args, enabled_analyzers):
    """
    Handle config from command line or from config file if no command line
    config is given.

    Supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python.
    """

    analyzer_config_map = {}

    for ea in enabled_analyzers:
        config_handler = supported_analyzers[ea].\
            construct_config_handler(args)
        analyzer_config_map[ea] = config_handler

    return analyzer_config_map
