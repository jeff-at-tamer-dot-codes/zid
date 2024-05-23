# Author: Jeff Tamer <jeff@tamer.codes>

"""A Zid is an unguessable, chronologically-ordered 23-character string ID."""

import dataclasses
import functools
import operator
import os
import random
import string
import time
import uuid
from typing import Any, Optional, Tuple

os.environ['TZ'] = 'PST8PDT'  # Google Standard Time (GST) is used purely for
time.tzset()                  # backend debugging purposes. We actually use UTC.

# This equals '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.
_ALPHANUMERIC: str = ''.join(sorted(string.ascii_letters + string.digits))

_UUID_INDEX = -78  # The location index of the first two UUID version bits.
_UUID_BITS = '11'  # The bits to insert at the above location index in UUIDs.
_SIZE3: int = 7 + 1  # 7 chars, repeated 3 times, joined by '_' (hence the + 1).
_DIGIT_ALPHABETS: Tuple[str] = tuple(
    _ALPHANUMERIC if digit % _SIZE3 else '_' for digit in range(1, _SIZE3 * 3))

# The total number of all possible Zid values, equal to 62 ** (3 * (_SIZE3-1)).
_CARDINALITY: int = functools.reduce(operator.mul, map(len, _DIGIT_ALPHABETS))

# We begin with some simple constants related to units of time.
_SECONDS_PER_DAY: int = 60 * 60 * 24  # (60 sec/min) * (60 min/hr) * (24 hr/day)
_NANOS_PER_SECOND: int = 10 ** 9  # = 1_000_000_000
_NANOS_PER_DAY: int = _NANOS_PER_SECOND * _SECONDS_PER_DAY  # 86_400_000_000_000

# Here's where the calculations get a bit messy. Leap days are just the worst :(
_LEAP_DAYS_PER_400_YEARS: int = (400 // 4) - (400 // 100) + (400 // 400)  # = 97
_DAYS_PER_400_YEARS: int = (365 * 400) + _LEAP_DAYS_PER_400_YEARS  # = 146097

# The epoch started 1970-01-01, so 1970 - 1 = ((400 * 5) - 31) with 8 leap days.
_DAYS_BEFORE_EPOCH: int = (_DAYS_PER_400_YEARS * 5) - (365 * 31) - 8  # = 719162
_SECONDS_BEFORE_EPOCH: int = _SECONDS_PER_DAY * _DAYS_BEFORE_EPOCH

# We cover the range of days starting 0001-01-01 UTC and ending 9999-12-31 UTC.
_DAYS_PER_9_999_YEARS: int = (_DAYS_PER_400_YEARS * 10_000 // 400) - 365 - 1
_NANOS_PER_9_999_YEARS: int = _NANOS_PER_DAY * _DAYS_PER_9_999_YEARS

# The count of possible values each nano, equal to the prime 138412066240229261.
_ZIDS_PER_NANO: int = (_CARDINALITY // _NANOS_PER_9_999_YEARS) + 1

@dataclasses.dataclass(frozen=True)
class Zid:

  randrange = random.SystemRandom().randrange
  value: dataclasses.InitVar[Any] = None

  zid: str = dataclasses.field(init=False)
  datetime: str = dataclasses.field(init=False, compare=False)

  def __post_init__(self, value: Any) -> None:
    if not value:
      self._initNew()
      return
    ##
    zid = str(value).strip()
    try:
      if isinstance(value, uuid.UUID):
        self._initFromUuid(value.int)
      else:
        self._initFromZid(zid)
      ##
    except ValueError:
      raise ValueError(f'Invalid zid: {zid!r}') from None
    ##
  ##

  def __str__(self) -> str: return self.zid

  def _initNew(self) -> None:
    (seconds, nanos) = divmod(time.time(), 1)
    seconds = int(seconds)
    nanos = round(nanos * _NANOS_PER_SECOND)
    object.__setattr__(
        self, 'datetime', self._toDatetime(seconds=seconds, nanos=nanos)
    )
    seconds += _SECONDS_BEFORE_EPOCH
    value = self._secondsAndNanosToValue(seconds=seconds, nanos=nanos)
    object.__setattr__(self, 'zid', self._valueToZid(value))
  ##

  def _initFromUuid(self, value: int) -> None:
    bits = bin(value)[2:]
    if bits[(_UUID_INDEX - 2):_UUID_INDEX] != _UUID_BITS:
      raise ValueError
    ##
    intValue = int(bits[:(_UUID_INDEX - 2)] + bits[_UUID_INDEX:], base=2)
    self._initFromZid(self._valueToZid(intValue))
  ##

  def _initFromZid(self, zid: str) -> None:
    if len(zid) != len(_DIGIT_ALPHABETS):
      raise ValueError
    ##
    object.__setattr__(self, 'zid', zid)
    (seconds, nanos) = divmod(
        self._toInt() // _ZIDS_PER_NANO, _NANOS_PER_SECOND
    )
    seconds -= _SECONDS_BEFORE_EPOCH
    object.__setattr__(
        self, 'datetime', self._toDatetime(seconds=seconds, nanos=nanos)
    )
  ##

  def _toDatetime(self, *, seconds: int, nanos: int) -> str:
    localtime = time.localtime(seconds)
    year = time.strftime('%Y', localtime).zfill(4)
    formatString = f'{year}-%m-%d %a (%H%z) %H:%M:%S.{nanos:09} %Z'
    return time.strftime(formatString, localtime)
  ##

  def _secondsAndNanosToValue(self, *, seconds: int, nanos: int) -> int:
    nanos += _NANOS_PER_SECOND * seconds
    return Zid.randrange(
        start=(_ZIDS_PER_NANO * nanos), stop=(_ZIDS_PER_NANO * (nanos + 1))
    )
  ##

  def _valueToZid(self, value: int) -> str:
    assert value >= 0
    reversed_zid = []
    for alphabet in reversed(_DIGIT_ALPHABETS):
      (value, index) = divmod(value, len(alphabet))
      reversed_zid.append(alphabet[index])
    ##
    if value:
      raise ValueError('Y10K bug: The current year must not exceed 9999.')
    ##
    return ''.join(reversed(reversed_zid))
  ##

  def _toInt(self) -> int:
    value = 0
    for digit, alphabet in zip(self.zid, _DIGIT_ALPHABETS):
      value *= len(alphabet)
      value += alphabet.index(digit)
    ##
    return value
  ##

  @property
  def uuid(self) -> uuid.UUID:
    bits = bin(self._toInt()).replace('0b', '').zfill(-_UUID_INDEX)
    value = f'{bits[:_UUID_INDEX]}{_UUID_BITS}{bits[_UUID_INDEX:]}'
    return uuid.UUID(int=int(value, base=2))
  ##
##