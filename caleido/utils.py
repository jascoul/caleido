import colander
from cornice.validators import colander_body_validator

OKStatus = colander.SchemaNode(colander.String(),
                               validator=colander.OneOf(['ok']))
ErrorStatus = colander.SchemaNode(colander.String(),
                                  validator=colander.OneOf(['error']))

class ErrorResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        @colander.instantiate()
        class errors(colander.SequenceSchema):
            @colander.instantiate()
            class error(colander.MappingSchema):
                name = colander.SchemaNode(colander.String())
                description = colander.SchemaNode(colander.String())
                location = colander.SchemaNode(colander.String())
        status = ErrorStatus


class StatusResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = ErrorStatus

def colander_bound_repository_body_validator(
    request, schema=None, deserializer=None, **kwargs):
    if schema:
        schema = schema.bind(repository=request.repository)
    for method in kwargs.get('response_schemas', {}):
        kwargs['response_schemas'][method] = kwargs[
            'response_schemas'][method].bind(repository=request.repository)
    return colander_body_validator(request, schema=schema, **kwargs)
