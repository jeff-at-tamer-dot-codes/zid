"""Zids are chronologically-ordered unique identifiers."""

import builtins
from datetime import UTC, datetime as _datetime, timedelta
import re
from secrets import randbelow
import string
from time import sleep
from typing import Optional
from uuid import UUID

def _values_per_micro() -> int:
  last_date = _datetime(year = 9999, month = 12, day = 31, tzinfo = UTC)
  delta = (last_date - _FIRST_DATE) + timedelta(days = 1)
  return ((1 << 120) // (1_000_000 * int(delta.total_seconds()))) + 1
##

__all__ = ['Zid']
_ALPHABET = ''.join(sorted(string.printable[:62]))
_FIRST_DATE = _datetime(year = 1, month = 1, day = 1, tzinfo = UTC)
_LAST_VALUE = 'zszWVIy_ZES2MJo_AMUmjwV'  # Zid.from_bytes(b'\xff' * 15)
_RE = re.compile('[Zz][0-9A-Za-z]{6}_[0-9A-Za-z]{7}_[0-9A-Za-z]{7}$')
_UUID_HEX_RE = re.compile('[0-9a-f]{12}8[0-9a-f]{3}8[0-9a-f]{15}')
_VALUES_PER_MICRO = _values_per_micro()

class Zid(str):
  """Zids are chronologically-ordered unique identifiers."""

  __slots__ = ()
  _previous_now: Optional[_datetime] = None

  def __new__(cls, value: Optional[str] = None, /) -> 'Zid':
    if cls is not Zid: raise TypeError
    if isinstance(value, Zid): return value
    if value is None: return Zid.from_datetime(Zid._now())
    if (not _RE.fullmatch(str_value := str(value))) or (_LAST_VALUE < str_value):
      raise ValueError(f'Invalid Zid: {value!r}')
    ##
    return str.__new__(Zid, str_value)
  ##

  @staticmethod
  def _now() -> _datetime:
    while Zid._previous_now == (now := _datetime.now(tz = UTC)): sleep(1e-6)
    Zid._previous_now = now
    return now
  ##

  @staticmethod
  def from_bytes(value: builtins.bytes, /) -> 'Zid':
    """Loads a Zid from its 15-byte representation."""
    if not isinstance(value, bytes): raise TypeError
    if len(value) != 15: raise ValueError(f'Expected 15 bytes, got {len(value)}')
    int_value = int.from_bytes(value)
    digits = []
    for index in range(20):
      (int_value, remainder) = divmod(int_value, 62)
      digits.append(_ALPHABET[remainder])
      if index % 7 == 6: digits.append('_')
    ##
    digits.append('Zz'[int_value])
    return Zid(''.join(reversed(digits)))
  ##

  @staticmethod
  def from_datetime(value: _datetime, /) -> 'Zid':
    """Creates a new Zid for the given datetime."""
    if not isinstance(value, _datetime): raise TypeError
    if not value.tzinfo: raise ValueError('Expected a timezone-aware datetime')
    int_value = (delta := value - _FIRST_DATE).microseconds
    delta = timedelta(days = delta.days, seconds = delta.seconds)
    int_value += 1_000_000 * int(delta.total_seconds())
    int_value *= _VALUES_PER_MICRO
    int_value += randbelow(min(_VALUES_PER_MICRO, (1 << 120) - int_value))
    return Zid.from_bytes(int_value.to_bytes(length = 15))
  ##

  @staticmethod
  def from_uuid(uuid: UUID) -> 'Zid':
    """Loads a Zid from its UUID representation."""
    hex_str = uuid.hex
    if not _UUID_HEX_RE.fullmatch(hex_str): raise ValueError(f'Invalid Zid UUID: {uuid!r}')
    return Zid.from_bytes(bytes.fromhex(hex_str[:12] + hex_str[13:16] + hex_str[17:]))
  ##

  @property
  def bytes(self) -> bytes:
    """Returns the 15-byte representation of this Zid."""
    value = int(self.startswith('z'))
    for digit in self[1:]:
      if digit == '_': continue
      value *= 62
      value += _ALPHABET.index(digit)
    ##
    return value.to_bytes(length = 15)
  ##

  @property
  def datetime(self) -> _datetime:
    """Returns this Zid's embedded timestamp as a UTC datetime."""
    value = int.from_bytes(self.bytes)
    return _FIRST_DATE + timedelta(microseconds = value // _VALUES_PER_MICRO)
  ##

  @property
  def uuid(self) -> UUID:
    """Returns the version 8 UUID representation of this Zid."""
    hex_str = hex(int.from_bytes(self.bytes) + (1 << 120))
    return UUID(hex = f'{hex_str[3:15]}8{hex_str[15:18]}8{hex_str[18:]}')
  ##
##

assert _LAST_VALUE == Zid.from_bytes(b'\xff' * 15)
