from datetime import UTC, datetime, timedelta
import re
from secrets import randbelow
import string
from typing import Any, Optional
from uuid import UUID

class Zid(str):
  """A chronologically-ordered 15-byte UUIDv8 with an embedded timestamp."""

  _BASE = 62
  _ALPHABET = ''.join(sorted(string.printable[:_BASE]))

  _SIZE_IN_BYTES = 15
  _UPPER_BOUND = 1 << (8 * _SIZE_IN_BYTES)

  _FIRST_DATE = datetime(year = 1, month = 1, day = 1, tzinfo = UTC)
  _LAST_DATE = datetime(year = 9999, month = 12, day = 31, tzinfo = UTC)
  _TIME_DELTA = (_LAST_DATE - _FIRST_DATE) + timedelta(days = 1)
  _MICROSECOND_COUNT = 1_000_000 * int(_TIME_DELTA.total_seconds())

  _VALUES_PER_MICRO = (_UPPER_BOUND // _MICROSECOND_COUNT) + 1

  _ZID_RE = re.compile('[Zz][0-9A-Za-z]{6}_[0-9A-Za-z]{7}_[0-9A-Za-z]{7}')
  _SHORT_ZID_RE = re.compile('[Zz][0-9A-Za-z]{20}')
  _UUID_HEX_RE = re.compile('[0-9a-f]{12}8[0-9a-f]{3}8[0-9a-f]{15}')

  _FINAL_ZID = ''

  _last_datetime = None

  __slots__ = (
    '_bytes',
    '_datetime',
    '_uuid',
  )

  def __new__(
    cls, zid: Optional[Any] = None, /, *, datetime: Optional[datetime] = None
  ):
    if isinstance(zid, Zid): return zid
    return cls._new_internal(zid = zid, datetime_ = datetime)
  ##

  @classmethod
  def _new_internal(
    cls, *, zid: Optional[Any], datetime_: Optional[datetime]
  ) -> 'Zid':
    if isinstance(zid, str): return cls._from_str(zid)
    if isinstance(zid, bytes): return cls._from_bytes(zid)
    if isinstance(zid, UUID): return cls._from_uuid(zid)
    if zid is not None: return cls._from_str(str(zid), original = zid)
    if datetime_ is None:
      datetime_ = cls._last_datetime
      while datetime_ == cls._last_datetime: datetime_ = datetime.now(tz = UTC)
      cls._last_datetime = datetime_
    ##
    delta = datetime_ - cls._FIRST_DATE
    value = delta.microseconds
    delta = timedelta(days = delta.days, seconds = delta.seconds)
    value += 1_000_000 * int(delta.total_seconds())
    value *= cls._VALUES_PER_MICRO
    value += randbelow(min(cls._VALUES_PER_MICRO, cls._UPPER_BOUND - value))
    return cls._from_bytes(value.to_bytes(length = cls._SIZE_IN_BYTES))
  ##

  @classmethod
  def _from_str(cls, str_: str, *, original: Optional[str] = None) -> 'Zid':
    if original is None: original = str_
    str_ = str(str_)
    if (len(str_) == 21) and cls._SHORT_ZID_RE.fullmatch(str_):
      str_ = f'{str_[:7]}_{str_[7:14]}_{str_[14:]}'
    ##
    if (cls._FINAL_ZID < str_) or not cls._ZID_RE.fullmatch(str_):
      raise ValueError(f'Invalid Zid: {original!r}')
    ##
    return super().__new__(cls, str_)
  ##

  @classmethod
  def _from_bytes(cls, bytes_: bytes) -> 'Zid':
    bytes_ = bytes(bytes_)
    if len(bytes_) != cls._SIZE_IN_BYTES: raise ValueError(
      f'Expected {cls._SIZE_IN_BYTES} bytes; received {len(bytes_)} byte(s).'
    )
    value = int.from_bytes(bytes_)
    digits = []
    for index in range(20):
      (value, remainder) = divmod(value, cls._BASE)
      digits.append(cls._ALPHABET[remainder])
      if index % 7 == 6: digits.append('_')
    ##
    digits.append('Zz'[value])
    zid = super().__new__(cls, ''.join(reversed(digits)))
    zid._bytes = bytes_
    return zid
  ##

  @classmethod
  def _from_uuid(cls, uuid: UUID) -> 'Zid':
    hex_str = uuid.hex
    if not cls._UUID_HEX_RE.fullmatch(hex_str):
      raise ValueError(f'Invalid Zid UUID: {uuid!r}')
    ##
    return cls._from_bytes(
      bytes.fromhex(hex_str[:12] + hex_str[13:16] + hex_str[17:])
    )
  ##

  def __init__(
    self, zid: Optional[Any] = None, /, *, datetime: Optional[datetime] = None
  ):
    if not ((zid is None) or (datetime is None) or (datetime == self.datetime)):
      raise ValueError(
        f'Zid({(str(zid) if isinstance(zid, Zid) else zid)!r}, datetime='
        f'{datetime!r}) is inconsistent; expected datetime={self.datetime!r}'
      )
    ##
  ##

  def __repr__(self): return f"Zid('{self}')"

  @property
  def bytes(self) -> bytes:
    if hasattr(self, '_bytes'): return self._bytes
    value = self.startswith('z')
    for digit in self[1:]:
      if digit == '_': continue
      value *= self._BASE
      value += self._ALPHABET.index(digit)
    ##
    self._bytes = value.to_bytes(length = self._SIZE_IN_BYTES)
    return self._bytes
  ##

  @property
  def datetime(self) -> datetime:
    if hasattr(self, '_datetime'): return self._datetime
    value = int.from_bytes(self.bytes)
    self._datetime = self._FIRST_DATE + timedelta(
      microseconds = value // self._VALUES_PER_MICRO
    )
    return self._datetime
  ##

  @property
  def uuid(self) -> UUID:
    if hasattr(self, '_uuid'): return self._uuid
    hex_str = hex(int.from_bytes(self.bytes) + self._UPPER_BOUND)
    self._uuid = UUID(hex = f'{hex_str[3:15]}8{hex_str[15:18]}8{hex_str[18:]}')
    return self._uuid
  ##
##

Zid._FINAL_ZID = Zid(b'\xff'*15)