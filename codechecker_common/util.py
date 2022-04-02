# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Util module.
"""


import errno
import itertools
import subprocess

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def arg_match(options, args):
    """Checks and selects the option string specified in 'options'
    that are present in parameter 'args'."""
    matched_args = []
    for option in options:
        if any([arg if option.startswith(arg) else None
                for arg in args]):
            matched_args.append(option)
            continue

    return matched_args


def chunks(iterator, n):
    """
    Yield the next chunk if an iterable object. A chunk consists of maximum n
    elements.
    """
    for first in iterator:
        rest_of_chunk = itertools.islice(iterator, 0, n - 1)
        yield itertools.chain([first], rest_of_chunk)


def is_binary_available(bin, env):
    """
    Simple check if the binary is available. A binary is available if it's
    executable with --version flag.
    """
    version_cmd = [bin, '--version']
    LOG.debug_analyzer(' '.join(version_cmd))
    try:
        res = subprocess.call(
            version_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        if not res:
            return True

        LOG.debug_analyzer('Failed to run: "%s"', ' '.join(version_cmd))
        return False

    except OSError as oerr:
        if oerr.errno == errno.ENOENT:
            LOG.error(oerr)
            LOG.error('Failed to run: "%s"', ' '.join(version_cmd))
            return False
