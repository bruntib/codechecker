# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
This module implements customised common types and associated operations
to be used in the ORM layer.
"""
import json
from typing import Any, AnyStr, Optional, Tuple, Union, cast
import zlib

from sqlalchemy.types import LargeBinary, TypeDecorator


def to_zlib_tag_prefix(kind: str, compression_level: int) -> bytes:
    if '@' in kind:
        raise ValueError("'kind' must NOT contain a '@' as it breaks the "
                         "encoding format!")
    return ("zlib[%d]:%s@" % (compression_level, kind)).encode()


def from_zlib_tag_prefix(buffer: bytes) -> Tuple[bytes, str, int]:
    """
    Splits and parses the tag in a ZLib-compressed binary buffer.
    Returns:
      - The actual compressed payload, without the prefix.
      - The kind of the object compressed within (user-defined tag).
      - The compression ratio marker.
    """
    split_marker = buffer.index('@'.encode())
    prefix, payload = buffer[:split_marker].decode(), buffer[split_marker + 1:]

    algorithm = prefix.split('[')[0]
    if algorithm != "zlib":
        raise ValueError("Compression tag '%s' does not match expected 'zlib'"
                         % algorithm)

    compression = int(prefix.split('[')[1].split(']')[0])
    kind = prefix.split(':')[1]

    return payload, kind, compression


def encode_zlib(value: AnyStr,
                kind: Optional[str] = None,
                compression_level=zlib.Z_BEST_COMPRESSION) -> bytes:
    """
    Encodes the given 'value' string or buffer to a tagged ZLib-compressed
    buffer. The buffer is then prefix-tagged with type and compression
    information useful during raw data inspection or recovery.
    """
    if kind is None:
        if isinstance(value, str):
            kind = "str"
        elif isinstance(value, bytes):
            kind = "blob"
        kind = cast(str, kind)

    buffer: bytes = value.encode() if isinstance(value, str) else value
    buffer = zlib.compress(buffer, compression_level)

    return to_zlib_tag_prefix(kind, compression_level) + buffer


def decode_zlib(buffer: bytes) -> Tuple[str, Union[str, bytes]]:
    """
    Decodes the given 'buffer', which is a ZLib-compressed and prefixed data
    as created by 'encode_zlib()'. Returns the 'kind' attribute that was saved
    in the tagging information, and the decoded payload.

    If 'kind' is "str", the decoded payload will be decoded into a string.
    Otherwise, it is returned as a raw 'bytes' buffer.
    """
    buffer, kind, _ = from_zlib_tag_prefix(buffer)
    buffer = zlib.decompress(buffer)
    return kind, buffer.decode() if kind == "str" else buffer


class ZLibCompressedString(TypeDecorator):
    """
    Stores arbitrary user-defined strings ('str') as a ZLib-compressed
    binary datum.
    """
    impl = LargeBinary
    client_type = str

    compression_level = zlib.Z_BEST_COMPRESSION

    def process_bind_param(self, value: Optional[client_type],
                           dialect: str) -> Optional[impl]:
        """
        Transform a bound parameter of a client-side query value to the value
        of the underlying implementation type, i.e., Python -> Database.
        """
        if value is None:
            return None

        return cast(LargeBinary, encode_zlib(value))

    def process_result_value(self, value: Optional[impl],
                             dialect: str) -> Optional[client_type]:
        """
        Transforms a value obtained from the underlying implementation type
        to the value (and type) expected by client code, i.e.,
        Database -> Python.
        """
        if value is None:
            return None

        _, decoded = decode_zlib(cast(bytes, value))
        return cast(str, decoded)


class ZLibCompressedJSON(TypeDecorator):
    """
    Stores an arbitrary JSON object as a serialised ZLib-compressed binary
    datum.
    """

    # Note that since SQLAlchemy 0.6, types.Binary is deprecated and
    # automatically redirects to types.LargeBinary instead.
    impl = LargeBinary
    client_type = Any

    compression_level = zlib.Z_BEST_COMPRESSION

    def process_bind_param(self, value: Optional[client_type],
                           dialect: str) -> Optional[impl]:
        """
        Transform a bound parameter of a client-side query value to the value
        of the underlying implementation type, i.e., Python -> Database.
        """
        if value is None:
            return None

        serialised = json.dumps(value, sort_keys=True)
        return cast(LargeBinary, encode_zlib(serialised))

    def process_result_value(self, value: Optional[impl],
                             dialect: str) -> Optional[client_type]:
        """
        Transforms a value obtained from the underlying implementation type
        to the value (and type) expected by client code, i.e.,
        Database -> Python.
        """
        if value is None:
            return None

        _, decoded = decode_zlib(cast(bytes, value))
        serialised = cast(str, decoded)
        return json.loads(serialised)
