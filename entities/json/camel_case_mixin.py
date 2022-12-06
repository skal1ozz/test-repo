""" marshmallow-dataclass need a mixin to work with camel - snake cases """
import uuid
from datetime import datetime

import marshmallow_dataclass
from marshmallow import pre_load, post_dump
from stringcase import snakecase, camelcase


def uuid_factory() -> str:
    """ Set unique UUID """
    return uuid.uuid4().__str__()


def timestamp_factory() -> int:
    """ Set current unix timestamp """
    return int(datetime.utcnow().timestamp() * 1000)


class CamelCaseMixin:
    """ Camel Case mixin """

    @pre_load
    def to_snake_case(self, data, **_kwargs):
        """ to snake case pre load method """
        return {snakecase(key): value for key, value in data.items()}

    @post_dump
    def to_camel_case(self, data, **_kwargs):
        """ to camel case post load method """
        return {camelcase(key): value for key, value in data.items()}

    @classmethod
    def get_schema(cls, *args, **kwargs):
        """ Get schema """
        return marshmallow_dataclass.class_schema(cls)(*args, **kwargs)
