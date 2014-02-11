# -*- coding: utf-8 -*-

from django.db.models import Field as _DjangoField
from django.db.models import (
    BooleanField as _DjangoBooleanField,
    SmallIntegerField as _DjangoSmallIntegerField,
    TextField as _DjangoTextField,
    IntegerField as _DjangoIntegerField,
    BigIntegerField as _DjangoBigIntegerField,
    FloatField as _DjangoFloatField,
    IPAddressField as _DjangoIPField
)


__all__ = [
    "BooleanField",
    "StringField",
    "ByteField",
    "ShortField",
    "IntegerField",
    "LongField",
    "FloatField",
    "DoubleField",
    "IPField",
]


class Field(_DjangoField):

    def __init__(self, *args, **kwargs):
        self.fulltext_index = kwargs.pop("fulltext_index", None)
        self.analyzer = kwargs.pop("analyzer", None)
        super(Field, self).__init__(*args, **kwargs)

    def get_placeholder(self, idx, db):
        return '?'


class BooleanField(_DjangoBooleanField, Field):
    pass


class StringField(_DjangoTextField, Field):
    pass


class ByteField(_DjangoIntegerField, Field):
    pass


class ShortField(_DjangoSmallIntegerField, Field):
    pass


class IntegerField(_DjangoIntegerField, Field):
    pass


class LongField(_DjangoBigIntegerField, Field):
    pass


class FloatField(_DjangoFloatField, Field):
    pass


class DoubleField(_DjangoFloatField, Field):
    pass


class IPField(_DjangoIPField, Field):
    pass

# TODO: ObjectField, TimeStampField
