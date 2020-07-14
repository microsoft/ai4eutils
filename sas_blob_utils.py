"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

This module contains helper functions for dealing with Shared Access Signatures
(SAS) tokens for Azure Blob Storage.

Documentation for Azure Blob Storage:
https://docs.microsoft.com/en-us/azure/developer/python/sdk/storage/storage-blob-readme

Documentation for SAS:
https://docs.microsoft.com/en-us/azure/storage/common/storage-sas-overview
"""
from datetime import datetime, timedelta
import io
from typing import (
    Any, AnyStr, Dict, IO, Iterable, List, Optional, Set, Tuple, Union)
from urllib import parse
import uuid

from tqdm import tqdm

from azure.storage.blob import (
    BlobClient,
    BlobProperties,
    ContainerClient,
    ContainerSasPermissions,
    generate_container_sas,
    upload_blob_to_url)
from azure.core.exceptions import ResourceNotFoundError


class SasBlob:
    """SAS URI: https://<account>.blob.windows.net/<container>?<sas_token>"""
    @staticmethod
    def _get_resource_reference(prefix: str) -> str:
        return '{}{}'.format(prefix, str(uuid.uuid4()).replace('-', ''))

    @staticmethod
    def get_client_from_uri(sas_uri: str) -> ContainerClient:
        return ContainerClient.from_container_url(sas_uri)

    @staticmethod
    def get_account_from_uri(sas_uri: str) -> str:
        url_parts = parse.urlsplit(sas_uri)
        loc = url_parts.netloc  # "<account>.blob.windows.net"
        return loc.split('.')[0]

    @staticmethod
    def get_container_from_uri(sas_uri: str) -> str:
        url_parts = parse.urlsplit(sas_uri)
        raw_path = url_parts.path[1:]  # remove leading "/" from path
        container = raw_path.split('/')[0]
        return container

    @staticmethod
    def get_blob_from_uri(sas_uri: str, unquote_blob: bool = True
                          ) -> Optional[str]:
        """Return the path to the blob from the root container if this sas_uri
        is for an individual blob; otherwise returns None.

        Args:
            sas_uri: Azure blob storage SAS token
            unquote_blob: Replace any %xx escapes by their single-character
                equivalent. Default True.

        Returns: Path to the blob from the root container or None.
        """
        # Get the entire path with all slashes after the container
        url_parts = parse.urlsplit(sas_uri)
        raw_path = url_parts.path[1:]  # remove leading "/" from path
        container = raw_path.split('/')[0]

        parts = raw_path.split(container + '/')
        if len(parts) < 2:
            return None

        blob = parts[1]  # first item is an empty string

        if unquote_blob:
            blob = parse.unquote(blob)

        return blob

    @staticmethod
    def get_sas_key_from_uri(sas_uri: str) -> Optional[str]:
        """Get the query part of the SAS token that contains permissions, access
        times and signature.

        Args:
            sas_uri: Azure blob storage SAS token

        Returns: Query part of the SAS token, or None if URI has no token.
        """
        url_parts = parse.urlsplit(sas_uri)
        sas_token = url_parts.query or None  # None if query is empty string
        return sas_token

    @staticmethod
    def get_resource_type_from_uri(sas_uri: str) -> Optional[str]:
        """Get the resource type pointed to by this SAS token.

        Args:
            sas_uri: Azure blob storage SAS token

        Returns: A string (either 'blob' or 'container') or None.
        """
        url_parts = parse.urlsplit(sas_uri)
        data = parse.parse_qs(url_parts.query)
        if 'sr' in data:
            types = data['sr']
            if 'b' in types:
                return 'blob'
            elif 'c' in types:
                return 'container'
        return None

    @staticmethod
    def get_permissions_from_uri(sas_uri: str) -> Set[str]:
        """Get the permissions given by this SAS token.

        Args:
            sas_uri: Azure blob storage SAS token

        Returns: A set containing some of 'read', 'write', 'delete' and 'list'.
            Empty set returned if no permission specified in sas_uri.
        """
        url_parts = parse.urlsplit(sas_uri)
        data = parse.parse_qs(url_parts.query)
        permissions_set = set()
        if 'sp' in data:
            permissions = data['sp'][0]
            if 'r' in permissions:
                permissions_set.add('read')
            if 'w' in permissions:
                permissions_set.add('write')
            if 'd' in permissions:
                permissions_set.add('delete')
            if 'l' in permissions:
                permissions_set.add('list')
        return permissions_set

    @staticmethod
    def get_all_query_parts(sas_uri: str) -> Dict[str, Any]:
        """Gets the SAS token parameters."""
        url_parts = parse.urlsplit(sas_uri)
        return parse.parse_qs(url_parts.query)

    @staticmethod
    def check_blob_existence(sas_uri: str,
                             provided_blob_name: Optional[str] = None) -> bool:
        """Checks whether a given URI points to an actual blob.

        Args:
            sas_uri: str, URI to a container or a blob
            provided_blob_name: optional str, name of blob
                must be given if sas_uri is a URI to a container
                overrides blob name in sas_uri if sas_uri is a URI to a blob

        Returns: bool, whether the sas_uri given points to an existing blob
        """
        blob_name = provided_blob_name or SasBlob.get_blob_from_uri(sas_uri)
        if blob_name is None:
            raise ValueError('Blob name not provided as an argument, and '
                             'cannot be identified from the URI.')

        account = SasBlob.get_account_from_uri(sas_uri)
        container = SasBlob.get_container_from_uri(sas_uri)
        container_url = f'https://{account}.blob.windows.net/{container}'
        container_client = ContainerClient.from_container_url(
            container_url, credential=SasBlob.get_sas_key_from_uri(sas_uri))

        # until Azure implements a proper BlobClient.exists() method, we can
        # only use try/except to determine blob existence
        # see: https://github.com/Azure/azure-sdk-for-python/issues/9507
        blob_client = container_client.get_blob_client(blob_name)
        try:
            blob_client.get_blob_properties()
        except ResourceNotFoundError:
            return False
        return True

    @staticmethod
    def list_blobs_in_container(
            sas_uri: str, max_number_to_list: int,
            blob_prefix: Optional[str] = None,
            blob_suffix: Optional[Union[str, Tuple[str]]] = None) -> List[str]:
        """Get a list of blob names/paths in this container.

        Args:
            sas_uri: Azure blob storage SAS token
            max_number_to_list: Maximum number of blob names/paths to list
            blob_prefix: Optional, a string as the prefix to blob names/paths to
                filter the results to those with this prefix
            blob_suffix: Optional, a string or a tuple of strings, to filter the
                results to those with this/these suffix(s). The blob names will
                be lowercased first before comparing with the suffix(es).

        Returns:
            sorted list of blob names, of length max_number_to_list or shorter.
        """
        print('listing blobs...')
        if (SasBlob.get_sas_key_from_uri(sas_uri) is not None
                and SasBlob.get_resource_type_from_uri(sas_uri) != 'container'):
            raise ValueError('The SAS token provided is not for a container.')

        if blob_prefix is not None and not isinstance(blob_prefix, str):
            raise ValueError('blob_prefix must be a str.')

        if (blob_suffix is not None
                and not isinstance(blob_suffix, str)
                and not isinstance(blob_suffix, tuple)):
            raise ValueError('blob_suffix must be a str or a tuple of strings')

        container_client = SasBlob.get_client_from_uri(sas_uri)
        generator = container_client.list_blobs(name_starts_with=blob_prefix)

        list_blobs = []

        with tqdm() as pbar:
            for blob in generator:
                if blob_suffix is None or blob.name.lower().endswith(blob_suffix):
                    list_blobs.append(blob.name)
                    pbar.update(1)
                    if len(list_blobs) == max_number_to_list:
                        break
        return sorted(list_blobs)  # sort for determinism

    @staticmethod
    def generate_writable_container_sas(account_name: str,
                                        account_key: str,
                                        container_name: str,
                                        access_duration_hrs: float) -> str:
        """Creates a container and returns a SAS URI with read/write/list
        permissions.

        Args:
            account_name: str, name of blob storage account
            account_key: str, account SAS token or account shared access key
            container_name: str, name of container to create, must not match an
                existing container in the given storage account
            access_duration_hrs: float

        Returns: str, URL to newly created container

        Raises: azure.core.exceptions.ResourceExistsError, if container already
            exists
        """
        account_url = f'https://{account_name}.blob.windows.net'
        container_client = ContainerClient(account_url=account_url,
                                           container_name=container_name,
                                           credential=account_key)
        container_client.create_container()

        permissions = ContainerSasPermissions(read=True, write=True, list=True)
        container_sas_token = generate_container_sas(
            account_name=account_name,
            container_name=container_name,
            account_key=account_key,
            permission=permissions,
            expiry=datetime.utcnow() + timedelta(hours=access_duration_hrs))

        return f'{account_url}/{container_name}?{container_sas_token}'

    @staticmethod
    def upload_blob(container_sas_uri: str, blob_name: str,
                    data: Union[Iterable[AnyStr], IO[AnyStr]]) -> str:
        """Creates a new blob of the given name from an IO stream.

        Args:
            container_sas_uri: str, URI to a container
            blob_name: str, name of blob to upload
            data: str, bytes, or IO stream
                if str, assumes utf-8 encoding

        Returns: str, URI to blob
        """
        blob_url = SasBlob.generate_blob_sas_uri(container_sas_uri, blob_name)
        upload_blob_to_url(blob_url, data=data)
        return blob_url

    @staticmethod
    def get_blob_to_stream(sas_uri: str) -> Tuple[io.BytesIO, BlobProperties]:
        """Downloads a blob to an IO stream.

        Args:
            sas_uri: str, URI to a blob

        Returns:
            output_stream: io.BytesIO
            blob_properties: BlobProperties

        Raises: azure.core.exceptions.ResourceNotFoundError, if sas_uri points
            to a non-existant blob
        """
        blob_client = BlobClient.from_blob_url(sas_uri)
        with io.BytesIO() as output_stream:
            blob_client.download_blob().readinto(output_stream)
        blob_properties = blob_client.get_blob_properties()
        return output_stream, blob_properties

    @staticmethod
    def generate_blob_sas_uri(container_sas_uri: str, blob_name: str) -> str:
        """
        Args:
            container_sas_uri: str, URI to blob storage container
            blob_name: str, name of blob

        Returns: str, blob URI
        """
        account_name = SasBlob.get_account_from_uri(container_sas_uri)
        container_name = SasBlob.get_container_from_uri(container_sas_uri)
        sas_token = SasBlob.get_sas_key_from_uri(container_sas_uri)

        account_url = f'https://{account_name}.blob.windows.net'
        blob_uri = f'{account_url}/{container_name}/{blob_name}'
        if sas_token is not None:
            blob_uri += '?{sas_token}'
        return blob_uri
