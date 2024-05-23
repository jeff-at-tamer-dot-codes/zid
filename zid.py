# TODO(jt): Downgrade from nanos to micros.

"""A Zid is an unguessable, chronologically-ordered 32-character string ID."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from secrets import choice, randbits
from string import ascii_lowercase, ascii_uppercase, digits
from time import time_ns
from typing import Optional
from uuid import UUID

class Zid(str):
  """A Zid is an unguessable, chronologically-ordered 32-character string ID."""

  _B64_ALPHABET: str = ascii_uppercase + ascii_lowercase + digits + '-_'
  _mapping: dict[str, str] = dict(zip(_B64_ALPHABET, sorted(_B64_ALPHABET))).get
  _reverse: dict[str, str] = dict(zip(sorted(_B64_ALPHABET), _B64_ALPHABET)).get

  def __new__(
    cls,
    zid: Optional[str] = None,
    /, *,
    timestamp_nanos: Optional[int] = None,
    uuid: Optional[UUID] = None,
  ):
    if zid is not None:
      return cls._new(timestamp_nanos = timestamp_nanos, uuid = uuid, zid = zid)
    ##
    if timestamp_nanos is None: nanos = time_ns()
    if uuid is None: uuid = cls._uuid4()
    if (timestamp_nanos is None) and (nanos < (timestamp_nanos := time_ns())):
      timestamp_nanos = choice(range(nanos, timestamp_nanos))
    ##
    zid_bytes = (timestamp_nanos + (1 << 63)).to_bytes(length = 8) + uuid.bytes
    zid_str = ''.join(map(cls._mapping, urlsafe_b64encode(zid_bytes).decode()))
    return super().__new__(cls, zid_str)
  ##

  @property
  def bytes(self) -> bytes:
    """Returns this Zid as a bytes object consisting of 24 bytes."""
    return urlsafe_b64decode(''.join(map(self._reverse, self)).encode())
  ##

  @property
  def datetime(self) -> datetime:
    """Returns the timestamp component of this Zid as a datetime."""
    return self._datetime()
  ##

  @property
  def timestamp_nanos(self) -> int:
    """Returns the timestamp component of this Zid in Epoch time nanos."""
    return int.from_bytes(self.bytes[:8]) - (1 << 63)
  ##

  @property
  def uuid(self) -> UUID:
    """Returns the Version 4 UUID component of this Zid."""
    return UUID(bytes = self.bytes[8:])
  ##

  def _datetime(self) -> datetime:
    return datetime.fromtimestamp(self.timestamp_nanos / 1e9)
  ##

  @classmethod
  def _new(cls, *, timestamp_nanos: int, uuid: UUID, zid: str):
    obj = super().__new__(cls, zid)
    assert zid == Zid(timestamp_nanos = obj.timestamp_nanos, uuid = obj.uuid)
    assert timestamp_nanos in [None, obj.timestamp_nanos]
    assert uuid in [None, obj.uuid]
    return obj
  ##

  @staticmethod
  def _uuid4() -> UUID:
    bits = randbits(60) | ((randbits(68) & (-1 - 0xb0004) | 0x40008) << 60)
    return UUID(int = bits)
  ##
##