import logging
import hashlib

import colander
from pyramid.httpexceptions import HTTPNotFound, HTTPPreconditionFailed

from cornice.resource import resource, view
from cornice.validators import colander_validator
from cornice import Service

from caleido.models import Blob
from caleido.resources import ResourceFactory, BlobResource

from caleido.exceptions import StorageError
from caleido.utils import (ErrorResponseSchema,
                           StatusResponseSchema,
                           OKStatus,
                           JsonMappingSchemaSerializerMixin,
                           colander_bound_repository_body_validator)


class BlobSchema(colander.MappingSchema, JsonMappingSchemaSerializerMixin):

    id = colander.SchemaNode(colander.Int())
    name = colander.SchemaNode(colander.String())
    bytes = colander.SchemaNode(colander.Int())

    blob_key = colander.SchemaNode(colander.String(), missing=colander.drop)
    format = colander.SchemaNode(colander.String(), missing=colander.drop)
    checksum = colander.SchemaNode(colander.String(), missing=colander.drop)
    upload_url = colander.SchemaNode(colander.String(), missing=colander.drop)


class BlobPostSchema(BlobSchema):
    # similar to blob schema, but id is optional
    id = colander.SchemaNode(colander.Int(), missing=colander.drop)

class BlobResponseSchema(colander.MappingSchema):
    body = BlobSchema()

class BlobListingResponseSchema(colander.MappingSchema):
    @colander.instantiate()
    class body(colander.MappingSchema):
        status = OKStatus
        total = colander.SchemaNode(colander.Int())
        offset = colander.SchemaNode(colander.Int())
        limit = colander.SchemaNode(colander.Int())

        @colander.instantiate()
        class records(colander.SequenceSchema):
            blob = BlobSchema()

class BlobListingRequestSchema(colander.MappingSchema):
    @colander.instantiate()
    class querystring(colander.MappingSchema):
        offset = colander.SchemaNode(colander.Int(),
                                   default=0,
                                   validator=colander.Range(min=0),
                                   missing=0)
        limit = colander.SchemaNode(colander.Int(),
                                    default=20,
                                    validator=colander.Range(0, 100),
                                    missing=20)


@resource(name='Blob',
          collection_path='/api/v1/blob/records',
          path='/api/v1/blob/records/{id}',
          tags=['blob'],
          cors_origins=('*', ),
          api_security=[{'jwt':[]}],
          factory=ResourceFactory(BlobResource))
class BlobRecordAPI(object):
    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission='view',
          response_schemas={
        '200': BlobResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def get(self):
        "Retrieve a Blob"

        result = BlobSchema().to_json(self.context.model.to_dict())
        return result

    @view(permission='delete',
          response_schemas={
        '200': StatusResponseSchema(description='Ok'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        '404': ErrorResponseSchema(description='Not Found'),
        })
    def delete(self):
        "Delete an Blob"
        self.context.delete()
        return {'status': 'ok'}

    @view(permission='add',
          schema=BlobPostSchema(),
          validators=(colander_bound_repository_body_validator,),
          cors_origins=('*', ),
          response_schemas={
        '201': BlobResponseSchema(description='Created'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized'),
        '403': ErrorResponseSchema(description='Forbidden'),
        })
    def collection_post(self):
        "Create a new Blob"
        blob = Blob.from_dict(self.request.validated)
        blob.blob_key = self.request.repository.blob.new_blobkey()
        try:
            self.context.put(blob)
        except StorageError as err:
            self.request.errors.status = 400
            self.request.errors.add('body', err.location, str(err))
            return

        self.request.response.status = 201
        result =  BlobSchema().to_json(blob.to_dict())
        result['upload_url'] = self.request.repository.blob.upload_url(
            result['blob_key'])
        return result


    @view(permission='view',
          schema=BlobListingRequestSchema(),
          validators=(colander_validator),
          cors_origins=('*', ),
          response_schemas={
        '200': BlobListingResponseSchema(description='Ok'),
        '400': ErrorResponseSchema(description='Bad Request'),
        '401': ErrorResponseSchema(description='Unauthorized')})
    def collection_get(self):
        offset = self.request.validated['querystring']['offset']
        limit = self.request.validated['querystring']['limit']
        order_by = [Blob.family_name.asc(), Blob.name.asc()]
        listing = self.context.search(
            offset=offset,
            limit=limit,
            order_by=order_by,
            format=format,
            principals=self.request.effective_principals)
        schema = BlobSchema()
        result = {'total': listing['total'],
                  'records': [],
                  'snippets': [],
                  'limit': limit,
                  'offset': offset,
                  'status': 'ok'}
        result['records'] = [schema.to_json(blob.to_dict())
                             for blob in listing['hits']]
        return result

blob_upload = Service(name='BlobUpload',
                     path='/api/v1/blob/upload/{blob_key}',
                     factory=ResourceFactory(BlobResource),
                     api_security=[{'jwt':[]}],
                     tags=['blob'],
                     cors_origins=('*', ))
@blob_upload.post(permission='upload')
def blob_upload_local_view(request):
    blob_key = request.matchdict['blob_key']

    request.context.from_blob_key(request.matchdict['blob_key'])
    if request.context.model is None:
        raise HTTPNotFound()

    blobstore = request.repository.blob
    if blobstore.blob_exists(blob_key):
        raise HTTPPreconditionFailed()

    blobstore.receive_blob(request, request.context)
    return BlobSchema().to_json(request.context.model.to_dict())

blob_transform = Service(name='BlobTransform',
                         path='/api/v1/blob/transform/{blob_key}',
                         factory=ResourceFactory(BlobResource),
                         api_security=[{'jwt':[]}],
                         tags=['blob'],
                         cors_origins=('*', ))
@blob_transform.post(permission='transform')
def blob_transform_view(request):
    blob_key = request.matchdict['blob_key']
    request.context.from_blob_key(blob_key)
    if request.context.model is None:
        raise HTTPNotFound()
    blobstore = request.repository.blob
    if not blobstore.blob_exists(blob_key):
        raise HTTPPreconditionFailed('File is missing')

    blobstore.transform_blob(request.context)
    return request.context.model.to_dict()


"""
blob_download = Service(name='BlobDownload',
                     path='/api/v1/blob/download/{blob_key}',
                     factory=ResourceFactory(BlobResource),
                     api_security=[{'jwt':[]}],
                     tags=['blob'],
                     cors_origins=('*', ))
@blob_download.get(permission='download')
def blob_download_local_view(request):
    blob_key = request.matchdict['blob_key']
    request.context.from_blob_key(blob_key)
    if request.context.model is None:
        raise HTTPNotFound()
    response = request.response
    response.content_type = request.context.model.format
    response.content_length = request.context.model.bytes
    request.repository.blob.serve_blob(request,
                                       response,
                                       request.context)
    return response

"""
