# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.
"""
Machinery for converting CrateDB database types to native Python data types.

https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#column-types
"""
import ipaddress
from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

ConverterFunction = Callable[[Optional[Any]], Optional[Any]]
ColTypesDefinition = Union[int, List[Union[int, "ColTypesDefinition"]]]


def _to_ipaddress(value: Optional[str]) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """
    https://docs.python.org/3/library/ipaddress.html
    """
    if value is None:
        return None
    return ipaddress.ip_address(value)


def _to_datetime(value: Optional[float]) -> Optional[datetime]:
    """
    https://docs.python.org/3/library/datetime.html
    """
    if value is None:
        return None
    return datetime.utcfromtimestamp(value / 1e3)


def _to_default(value: Optional[Any]) -> Optional[Any]:
    return value


# Symbolic aliases for the numeric data type identifiers defined by the CrateDB HTTP interface.
# https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#column-types
class DataType(Enum):
    NULL = 0
    NOT_SUPPORTED = 1
    CHAR = 2
    BOOLEAN = 3
    TEXT = 4
    IP = 5
    DOUBLE = 6
    REAL = 7
    SMALLINT = 8
    INTEGER = 9
    BIGINT = 10
    TIMESTAMP_WITH_TZ = 11
    OBJECT = 12
    GEOPOINT = 13
    GEOSHAPE = 14
    TIMESTAMP_WITHOUT_TZ = 15
    UNCHECKED_OBJECT = 16
    REGPROC = 19
    TIME = 20
    OIDVECTOR = 21
    NUMERIC = 22
    REGCLASS = 23
    DATE = 24
    BIT = 25
    JSON = 26
    CHARACTER = 27
    ARRAY = 100


ConverterMapping = Dict[DataType, ConverterFunction]


# Map data type identifier to converter function.
_DEFAULT_CONVERTERS: ConverterMapping = {
    DataType.IP: _to_ipaddress,
    DataType.TIMESTAMP_WITH_TZ: _to_datetime,
    DataType.TIMESTAMP_WITHOUT_TZ: _to_datetime,
}


class Converter:
    def __init__(
        self,
        mappings: Optional[ConverterMapping] = None,
        default: ConverterFunction = _to_default,
    ) -> None:
        self._mappings = mappings or {}
        self._default = default

    def get(self, type_: ColTypesDefinition) -> ConverterFunction:
        if isinstance(type_, int):
            return self._mappings.get(DataType(type_), self._default)
        type_, inner_type = type_
        if DataType(type_) is not DataType.ARRAY:
            raise ValueError(f"Data type {type_} is not implemented as collection type")

        inner_convert = self.get(inner_type)

        def convert(value: Any) -> Optional[List[Any]]:
            if value is None:
                return None
            return [inner_convert(x) for x in value]

        return convert

    def set(self, type_: DataType, converter: ConverterFunction):
        self._mappings[type_] = converter


class DefaultTypeConverter(Converter):
    def __init__(self, more_mappings: Optional[ConverterMapping] = None) -> None:
        mappings: ConverterMapping = {}
        mappings.update(deepcopy(_DEFAULT_CONVERTERS))
        if more_mappings:
            mappings.update(deepcopy(more_mappings))
        super().__init__(
            mappings=mappings, default=_to_default
        )
