# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
from typing import Tuple, cast
import zlib

from codechecker_server.database.common import decode_zlib, encode_zlib


def raw_zlib_encode_buf(value: bytes) -> bytes:
    """
    Encodes the given 'value' binary buffer with ZLib's Z_BEST_COMPRESSION.
    """
    return zlib.compress(value, zlib.Z_BEST_COMPRESSION)


def raw_zlib_decode_buf(value: bytes) -> bytes:
    """
    Decodes the given ZLib-compressed 'value' into a binary buffer.
    """
    return zlib.decompress(value)


def raw_zlib_decode_str(value: bytes) -> str:
    """
    Decodes the given ZLib-compressed 'value' into a string.
    """
    return raw_zlib_decode_buf(value).decode("utf-8", errors="ignore")


def recompress_zlib_as_tagged(value: bytes, kind: str = "str") -> bytes:
    """
    Recompresses the given raw ZLib-compressed 'value' by tagging it with the
    'kind' to be usable with the 'ZLibCompressed*' BLOB column adaptors.

    This method always encodes using Z_BEST_COMPRESSION as the compression
    strategy.
    """
    try:
        raw = raw_zlib_decode_str(value).encode()
        kind = "str"
    except UnicodeDecodeError:
        raw = raw_zlib_decode_buf(value)
        kind = "blob"

    return encode_zlib(raw, kind)


def recompress_zlib_as_untagged(value: bytes) -> bytes:
    """
    Recompresses the given tagged and ZLib-compressed 'value' as a raw
    ZLib-compressed binary buffer without any additional tags.

    This method always encodes using Z_BEST_COMPRESSION as the compression
    strategy.
    """
    kind, payload = decode_zlib(value)
    payload = cast(bytes,
                   cast(str, payload).encode() if kind == "str" else payload)

    return raw_zlib_encode_buf(payload)


def recompress_zlib_as_tagged_exact_ratio(
    value: bytes,
    kind: str = "str"
) -> Tuple[int, bytes]:
    """
    Recompresses the given raw ZLib-compressed 'value' by tagging it with the
    'kind' to be usable with the 'ZLibCompressed*' BLOB column adaptors.

    This method is more costly as it searches for the exact compression ratio
    that was originally used by performing up to 11 rounds of re-encoding
    internally until the compression ratio is figured out. Unfortunately, there
    are no good and deterministic ways to recover this information in a single
    go.

    The exact compression ratio might not be found, e.g., if the zlib version
    used to encode the original 'value' no longer matches what is available
    on the current machine, and all possible compression ratios produce a
    different result than originally present. In this case, Z_BEST_COMPRESSION
    will be used for the re-compressed buffer.
    """
    data = raw_zlib_decode_buf(value)

    def _attempt(level: int) -> bool:
        return zlib.compress(data, level) == value

    level_to_use = zlib.Z_BEST_COMPRESSION
    for compression_level in reversed(range(-1, 10)):
        if _attempt(compression_level):
            # Found a matching compression ratio, use this one.
            level_to_use = compression_level
            break

    return level_to_use, encode_zlib(data, kind, level_to_use)
