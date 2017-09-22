import colander

class ErrorMessageSchema(colander.MappingSchema):
    name = colander.SchemaNode(colander.String())
    description = colander.SchemaNode(colander.String())
    location = colander.SchemaNode(colander.String())
    
class ErrorListSchema(colander.SequenceSchema):
    error = ErrorMessageSchema()

class ErrorSchema(colander.MappingSchema):
    errors = ErrorListSchema()
    status = colander.SchemaNode(colander.String())
    
class ErrorBodySchema(colander.MappingSchema):
    body = ErrorSchema()
    
