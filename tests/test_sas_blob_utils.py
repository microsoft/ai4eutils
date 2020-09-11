"""
Unit tests for sas_blob_utils.py

In order to test "uploading" blobs without exposing private SAS keys, we use
the Azurite blob storage emulator instead. Instructions for installing:

Azurite documentation:
https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azurite
https://github.com/azure/azurite

1) Install nodejs. Many ways to do so, but perhaps the easiest is via conda:
    conda create -n node -c conda-forge nodejs
    conda activate node

2) Install Azurite from npm. The -g option installs the package globally.
    npm install -g azurite

3) Run Azurite. The -l flag sets a temp folder where Azurite can store data to
disk. By default, Azurite's blob service runs at 127.0.0.1:10000, which can be
changed by the parameters --blobHost 1.2.3.4 --blobPort 5678.
    mkdir -p $HOME/tmp/azurite
    rm -r $HOME/tmp/azurite/*  # if the folder already existed, clear it
    azurite-blob -l $HOME/tmp/azurite

4) In a separate terminal, activate a virtual environment with the Azure Storage
Python SDK v12, navigate to the ai4eutils folder, and run:
    # run all tests, -v for verbose output
    python -m unittest -v tests/test_sas_blob_utils.py

    # run a specific test
    python -m unittest -v tests.test_sas_blob_utils.Tests.test_build_blob_uri

Azurite by default supports the following storage account:
- Account name: devstoreaccount1
- Account key: Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==  # pylint: disable=line-too-long
"""
import unittest

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.storage.blob import BlobClient, ContainerClient

from sas_blob_utils import (
    build_blob_uri,
    check_blob_exists,
    download_blob_to_stream,
    generate_writable_container_sas,
    get_account_from_uri,
    get_blob_from_uri,
    get_container_from_uri,
    get_sas_token_from_uri,
    list_blobs_in_container,
    upload_blob)


PUBLIC_CONTAINER_URI = 'https://lilablobssc.blob.core.windows.net/nacti-unzipped'  # pylint: disable=line-too-long
PUBLIC_CONTAINER_SAS = 'st=2020-01-01T00%3A00%3A00Z&se=2034-01-01T00%3A00%3A00Z&sp=rl&sv=2019-07-07&sr=c&sig=rsgUcvoniBu/Vjkjzubh6gliU3XGvpE2A30Y0XPW4Vc%3D'  # pylint: disable=line-too-long
PUBLIC_CONTAINER_URI_SAS = f'{PUBLIC_CONTAINER_URI}?{PUBLIC_CONTAINER_SAS}'
PUBLIC_BLOB_NAME = 'part0/sub000/2010_Unit150_Ivan097_img0003.jpg'
PUBLIC_INVALID_BLOB_NAME = 'part0/sub000/2010_Unit150_Ivan000_img0003.jpg'
PUBLIC_BLOB_URI = f'{PUBLIC_CONTAINER_URI}/{PUBLIC_BLOB_NAME}'
PUBLIC_BLOB_URI_SAS = f'{PUBLIC_BLOB_URI}?{PUBLIC_CONTAINER_SAS}'
PUBLIC_INVALID_BLOB_URI = f'{PUBLIC_CONTAINER_URI}/{PUBLIC_INVALID_BLOB_NAME}'

PUBLIC_ZIPPED_CONTAINER_URI = 'https://lilablobssc.blob.core.windows.net/wcs'

# Azurite defaults
PRIVATE_ACCOUNT_NAME = 'devstoreaccount1'
PRIVATE_ACCOUNT_KEY = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='  # pylint: disable=line-too-long
PRIVATE_ACCOUNT_URI = f'http://127.0.0.1:10000/{PRIVATE_ACCOUNT_NAME}'
PRIVATE_CONTAINER_NAME = 'mycontainer'
PRIVATE_CONTAINER_URI = f'{PRIVATE_ACCOUNT_URI}/{PRIVATE_CONTAINER_NAME}'
PRIVATE_BLOB_NAME = 'successdir/successblob'
PRIVATE_BLOB_URI = f'{PRIVATE_CONTAINER_URI}/{PRIVATE_BLOB_NAME}'


class Tests(unittest.TestCase):
    """Tests for sas_blob_utils.py"""

    needs_cleanup = False

    def tearDown(self):
        if self.needs_cleanup:
            # cleanup: delete the private emulated container
            print('running cleanup')

            with BlobClient(account_url=PRIVATE_ACCOUNT_URI,
                            container_name=PRIVATE_CONTAINER_NAME,
                            blob_name=PRIVATE_BLOB_NAME,
                            credential=PRIVATE_ACCOUNT_KEY) as bc:
                if bc.exists():
                    print('deleted blob')
                    bc.delete_blob(delete_snapshots='include')

            with ContainerClient.from_container_url(
                    PRIVATE_CONTAINER_URI,
                    credential=PRIVATE_ACCOUNT_KEY) as cc:
                try:
                    cc.get_container_properties()
                    cc.delete_container()
                    print('deleted container')
                except ResourceNotFoundError:
                    pass
        self.needs_cleanup = False

    def test_get_account_from_uri(self):
        self.assertEqual(get_account_from_uri(PUBLIC_BLOB_URI), 'lilablobssc')

    def test_get_container_from_uri(self):
        self.assertEqual(
            get_container_from_uri(PUBLIC_BLOB_URI),
            'nacti-unzipped')

    def test_get_blob_from_uri(self):
        self.assertEqual(get_blob_from_uri(PUBLIC_BLOB_URI), PUBLIC_BLOB_NAME)
        with self.assertRaises(ValueError):
            get_blob_from_uri(PUBLIC_CONTAINER_URI)

    def test_get_sas_token_from_uri(self):
        self.assertIsNone(get_sas_token_from_uri(PUBLIC_CONTAINER_URI))
        self.assertEqual(
            get_sas_token_from_uri(PUBLIC_CONTAINER_URI_SAS),
            PUBLIC_CONTAINER_SAS)

    def test_check_blob_exists(self):
        print('PUBLIC_BLOB_URI')
        self.assertTrue(check_blob_exists(PUBLIC_BLOB_URI))
        print('PUBLIC_CONTAINER_URI + PUBLIC_BLOB_NAME')
        self.assertTrue(check_blob_exists(
            PUBLIC_CONTAINER_URI, blob_name=PUBLIC_BLOB_NAME))

        print('PUBLIC_CONTAINER_URI')
        with self.assertRaises(IndexError):
            check_blob_exists(PUBLIC_CONTAINER_URI)
        print('PUBLIC_INVALID_BLOB_URI')
        self.assertFalse(check_blob_exists(PUBLIC_INVALID_BLOB_URI))

    def test_list_blobs_in_container(self):
        blobs_list = list_blobs_in_container(
            PUBLIC_ZIPPED_CONTAINER_URI, limit=100)
        expected = sorted([
            'wcs_20200403_bboxes.json.zip', 'wcs_camera_traps.json.zip',
            'wcs_camera_traps_00.zip', 'wcs_camera_traps_01.zip',
            'wcs_camera_traps_02.zip', 'wcs_camera_traps_03.zip',
            'wcs_camera_traps_04.zip', 'wcs_camera_traps_05.zip',
            'wcs_camera_traps_06.zip', 'wcs_specieslist.csv',
            'wcs_splits.json'])
        self.assertEqual(blobs_list, expected)

        blobs_list = list_blobs_in_container(
            PUBLIC_ZIPPED_CONTAINER_URI, rsearch=r'_\d[0-3]\.zip')
        expected = sorted([
            'wcs_camera_traps_00.zip', 'wcs_camera_traps_01.zip',
            'wcs_camera_traps_02.zip', 'wcs_camera_traps_03.zip'])
        self.assertEqual(blobs_list, expected)

    def test_generate_writable_container_sas(self):
        self.needs_cleanup = True
        new_sas_uri = generate_writable_container_sas(
            account_name=PRIVATE_ACCOUNT_NAME,
            account_key=PRIVATE_ACCOUNT_KEY,
            container_name=PRIVATE_CONTAINER_NAME,
            access_duration_hrs=1,
            account_url=PRIVATE_ACCOUNT_URI)
        self.assertTrue(isinstance(new_sas_uri, str))
        self.assertNotEqual(new_sas_uri, '')
        self.assertEqual(len(list_blobs_in_container(new_sas_uri)), 0)

    def test_upload_blob(self):
        self.needs_cleanup = True
        # uploading to a read-only public container without a SAS token yields
        # HttpResponseError('Server failed to authenticate the request.')
        print('PUBLIC_CONTAINER_URI')
        with self.assertRaises(HttpResponseError):
            upload_blob(PUBLIC_CONTAINER_URI,
                        blob_name='failblob', data='fail')

        # uploading to a public container with a read-only SAS token yields
        # HttpResponseError('This request is not authorized to perform this '
        #                   'operation using this permission.')
        print('PUBLIC_CONTAINER_URI_SAS')
        with self.assertRaises(HttpResponseError):
            upload_blob(PUBLIC_CONTAINER_URI_SAS,
                        blob_name='failblob', data='fail')

        # uploading to a private container without a SAS token yields
        # HttpResponseError('Server failed to authenticate the request. Make '
        #                   'sure the value of the Authorization header is '
        #                   'formed correctly including the signature.')
        print('PRIVATE_CONTAINER_URI')
        with self.assertRaises(HttpResponseError):
            upload_blob(PRIVATE_CONTAINER_URI,
                        blob_name=PRIVATE_BLOB_NAME, data='success')

        # upload to a private container with a SAS token
        private_container_uri_sas = generate_writable_container_sas(
            account_name=PRIVATE_ACCOUNT_NAME,
            account_key=PRIVATE_ACCOUNT_KEY,
            container_name=PRIVATE_CONTAINER_NAME,
            access_duration_hrs=1,
            account_url=PRIVATE_ACCOUNT_URI)
        container_sas = get_sas_token_from_uri(private_container_uri_sas)
        private_blob_uri_sas = f'{PRIVATE_BLOB_URI}?{container_sas}'
        blob_url = upload_blob(
            private_container_uri_sas,
            blob_name=PRIVATE_BLOB_NAME, data='success')
        self.assertEqual(blob_url, private_blob_uri_sas)

        with BlobClient(account_url=PRIVATE_ACCOUNT_URI,
                        container_name=PRIVATE_CONTAINER_NAME,
                        blob_name=PRIVATE_BLOB_NAME,
                        credential=container_sas) as blob_client:
            self.assertTrue(blob_client.exists())

    def test_download_blob_to_stream(self):
        output, props = download_blob_to_stream(PUBLIC_BLOB_URI)
        x = output.read()
        self.assertEqual(len(x), 376645)
        output.close()

        expected_properties = {
            'size': 376645,
            'name': PUBLIC_BLOB_NAME,
            'container': 'nacti-unzipped'
        }

        for k, v in expected_properties.items():
            self.assertEqual(props[k], v)

    def test_build_blob_uri(self):
        generated = build_blob_uri(
            container_uri=PUBLIC_CONTAINER_URI,
            blob_name=PUBLIC_BLOB_NAME)
        self.assertEqual(generated, PUBLIC_BLOB_URI)

        generated = build_blob_uri(
            container_uri=PUBLIC_CONTAINER_URI_SAS,
            blob_name=PUBLIC_BLOB_NAME)
        self.assertEqual(generated, PUBLIC_BLOB_URI_SAS)


if __name__ == '__main__':
    unittest.main()
