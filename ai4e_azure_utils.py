#
# ai4e_azure_utils.py
#
# Miscellaneous Azure utilities
#
import json
import re
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

from azure.storage.blob._models import BlobPrefix
from azure.storage.blob import ContainerClient

import sas_blob_utils


# Based on:
#
# https://github.com/Azure/azure-sdk-for-python/blob/master/sdk/storage/azure-storage-blob/samples/blob_samples_walk_blob_hierarchy.py
def walk_container(container_client, max_depth=-1, prefix='',
                   store_folders=True, store_blobs=True, debug_max_items=-1):
    """
    Recursively walk folders in the ContainerClient object *container_client*
    """

    depth =  1

    def walk_blob_hierarchy(prefix=prefix, folders=None, blobs=None):

        if folders is None:
            folders = []
        if blobs is None:
            blobs = []

        nonlocal depth

        if max_depth > 0 and depth > max_depth:
            return folders, blobs

        for item in container_client.walk_blobs(name_starts_with=prefix):
            short_name = item.name[len(prefix):]
            if isinstance(item, BlobPrefix):
                # print('F: ' + prefix + short_name)
                if store_folders:
                    folders.append(prefix + short_name)
                depth += 1
                walk_blob_hierarchy(prefix=item.name, folders=folders, blobs=blobs)
                if (debug_max_items > 0) and (len(folders)+len(blobs) > debug_max_items):
                    return folders, blobs
                depth -= 1
            else:
                if store_blobs:
                    blobs.append(prefix + short_name)

        return folders, blobs

    folders, blobs = walk_blob_hierarchy()

    assert(all([s.endswith('/') for s in folders]))
    folders = [s.strip('/') for s in folders]

    return folders, blobs


def list_top_level_blob_folders(container_client: ContainerClient) -> List[str]:
    """
    List all top-level folders in the ContainerClient object *container_client*
    """
    top_level_folders, _ = walk_container(
        container_client, max_depth=1, store_blobs=False)
    return top_level_folders


#%% Blob enumeration

def concatenate_json_lists(input_files: Iterable[str],
                           output_file: Optional[str] = None
                           ) -> List[Any]:
    """Given a list of JSON files that contain lists (typically string
    filenames), concatenates the lists into a single list and optionally
    writes out this list to a new output JSON file.
    """
    output_list = []
    for fn in input_files:
        with open(fn, 'r') as f:
            file_list = json.load(f)
        output_list.extend(file_list)
    if output_file is not None:
        with open(output_file, 'w') as f:
            json.dump(output_list, f, indent=1)
    return output_list


def write_list_to_file(output_file: str, strings: Sequence[str]) -> None:
    """Writes a list of strings to either a JSON file or text file,
    depending on extension of the given file name.
    """
    with open(output_file, 'w') as f:
        if output_file.endswith('.json'):
            json.dump(strings, f, indent=1)
        else:
            f.write('\n'.join(strings))


def read_list_from_file(filename: str):
    """Reads a json-formatted list of strings from a file."""
    assert filename.endswith('.json')
    with open(filename, 'r') as f:
        file_list = json.load(f)
    assert isinstance(file_list, list)
    for s in file_list:
        assert isinstance(s, str)
    return file_list


def upload_file_to_blob(account_name: str,
                        container_name: str,
                        local_path: str,
                        blob_name: str,
                        sas_token: Optional[str] = None) -> str:
    """Uploads a local file to Azure Blob Storage and returns the uploaded
    blob URI (without a SAS token)."""
    container_uri = sas_blob_utils.build_azure_storage_uri(
        account=account_name, container=container_name, sas_token=sas_token)
    with open(local_path, 'rb') as data:
        return sas_blob_utils.upload_blob(
            container_uri=container_uri, blob_name=blob_name, data=data)


def enumerate_blobs_to_file(
        output_file: str,
        account_name: str,
        container_name: str,
        sas_token: Optional[str] = None,
        blob_prefix: Optional[str] = None,
        blob_suffix: Optional[Union[str, Tuple[str]]] = None,
        rsearch: Optional[str] = None,
        limit: Optional[str] = None
        ) -> List[str]:
    """
    Enumerates to a .json string if output_file ends in ".json", otherwise enumerates to a
    newline-delimited list.

    See enumerate_blobs for parameter information.
    """
    container_uri = sas_blob_utils.build_azure_storage_uri(
        account=account_name, container=container_name, sas_token=sas_token)
    matched_blobs = sas_blob_utils.list_blobs_in_container(
        container_uri=container_uri, blob_prefix=blob_prefix,
        blob_suffix=blob_suffix, rsearch=rsearch, limit=limit)
    write_list_to_file(output_file, matched_blobs)
    return matched_blobs
