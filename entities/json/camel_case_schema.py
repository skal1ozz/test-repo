""" Camel Case schema implementation """
from marshmallow import Schema, fields, EXCLUDE


def camelcase(s):
    """ Convert camel case to snake case"""
    parts = iter(s.split("_"))
    return next(parts) + "".join(i.title() for i in parts)


class CamelCaseSchema(Schema):
    """Schema that uses camel-case for its external representation
    and snake-case for its internal representation.
    """

    def on_bind_field(self, field_name, field_obj):
        """ On bind field callback """
        field_obj.data_key = camelcase(field_obj.data_key or field_name)

    class Meta:
        """ Meta config """
        unknown = EXCLUDE
