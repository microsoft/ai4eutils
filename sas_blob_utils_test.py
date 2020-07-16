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
    mkdir $HOME/tmp/azurite
    azurite-blob -l $HOME/tmp/azurite

4) Now we can run this unit test:
    python test_sas_blob_utils.py -v

Azurite by default supports the following storage account:
- Account name: devstoreaccount1
- Account key: Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==
"""

import unittest

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from sas_blob_utils import BlobClient, ContainerClient, SasBlob


PUBLIC_CONTAINER_URI = 'https://lilablobssc.blob.core.windows.net/nacti-unzipped'
PUBLIC_CONTAINER_SAS = 'st=2020-01-01T00%3A00%3A00Z&se=2034-01-01T00%3A00%3A00Z&sp=rl&sv=2019-07-07&sr=c&sig=rsgUcvoniBu/Vjkjzubh6gliU3XGvpE2A30Y0XPW4Vc%3D'
PUBLIC_CONTAINER_URI_WITH_SAS = f'{PUBLIC_CONTAINER_URI}?{PUBLIC_CONTAINER_SAS}'
PUBLIC_BLOB_NAME = 'part0/sub000/2010_Unit150_Ivan097_img0003.jpg'
PUBLIC_INVALID_BLOB_NAME = 'part0/sub000/2010_Unit150_Ivan000_img0003.jpg'
PUBLIC_BLOB_URI = f'{PUBLIC_CONTAINER_URI}/{PUBLIC_BLOB_NAME}'
PUBLIC_BLOB_URI_WITH_SAS = f'{PUBLIC_BLOB_URI}?{PUBLIC_CONTAINER_SAS}'
PUBLIC_INVALID_BLOB_URI = f'{PUBLIC_CONTAINER_URI}/{PUBLIC_INVALID_BLOB_NAME}'

PUBLIC_ZIPPED_CONTAINER_URI = 'https://lilablobssc.blob.core.windows.net/wcs'

# Azurite defaults
PRIVATE_ACCOUNT_NAME = 'devstoreaccount1'
PRIVATE_ACCOUNT_KEY = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='
PRIVATE_ACCOUNT_URI = f'http://127.0.0.1:10000/{PRIVATE_ACCOUNT_NAME}'
PRIVATE_CONTAINER_NAME = 'mycontainer'
PRIVATE_CONTAINER_URI = f'{PRIVATE_ACCOUNT_URI}/{PRIVATE_CONTAINER_NAME}'
PRIVATE_BLOB_NAME = 'successdir/successblob'
PRIVATE_BLOB_URI = f'{PRIVATE_CONTAINER_URI}/{PRIVATE_BLOB_NAME}'


class TestSasBlobUtils(unittest.TestCase):
    needs_cleanup = False

    def tearDown(self):
        if self.needs_cleanup:
            # cleanup: delete the private emulated container
            print('running cleanup')

            # until the private emulated account is able to work, skip cleanup
            # with ContainerClient.from_container_url(
            #         PRIVATE_CONTAINER_URI,
            #         credential=PRIVATE_ACCOUNT_KEY) as cc:
            #     try:
            #         cc.get_container_properties()
            #         cc.delete_container()
            #     except ResourceNotFoundError:
            #         pass

            # if SasBlob.check_blob_existence(PRIVATE_BLOB_URI):
            #     with BlobClient.from_blob_url(
            #             PRIVATE_BLOB_URI,
            #             credential=PRIVATE_ACCOUNT_KEY) as bc:
            #         bc.delete_blob(delete_snapshots=True)
        self.needs_cleanup = False

    def test_get_account_from_uri(self):
        self.assertEqual(
            SasBlob.get_account_from_uri(PUBLIC_BLOB_URI),
            'lilablobssc')

    def test_get_container_from_uri(self):
        self.assertEqual(
            SasBlob.get_container_from_uri(PUBLIC_BLOB_URI),
            'nacti-unzipped')

    def test_get_blob_from_uri(self):
        self.assertEqual(
            SasBlob.get_blob_from_uri(PUBLIC_BLOB_URI),
            PUBLIC_BLOB_NAME)
        with self.assertRaises(ValueError):
            SasBlob.get_blob_from_uri(PUBLIC_CONTAINER_URI)

    def test_get_sas_key_from_uri(self):
        self.assertIsNone(SasBlob.get_sas_key_from_uri(PUBLIC_CONTAINER_URI))
        self.assertEqual(
            SasBlob.get_sas_key_from_uri(PUBLIC_CONTAINER_URI_WITH_SAS),
            PUBLIC_CONTAINER_SAS)

    def test_check_blob_existence(self):
        print('PUBLIC_BLOB_URI')
        self.assertTrue(SasBlob.check_blob_existence(PUBLIC_BLOB_URI))
        print('PUBLIC_CONTAINER_URI + PUBLIC_BLOB_NAME')
        self.assertTrue(SasBlob.check_blob_existence(
            PUBLIC_CONTAINER_URI, blob_name=PUBLIC_BLOB_NAME))

        print('PUBLIC_CONTAINER_URI')
        with self.assertRaises(IndexError):  
            SasBlob.check_blob_existence(PUBLIC_CONTAINER_URI)
        print('PUBLIC_INVALID_BLOB_URI')
        self.assertFalse(SasBlob.check_blob_existence(PUBLIC_INVALID_BLOB_URI))

        print('PRIVATE_BLOB_URI')
        with self.assertRaises(HttpResponseError):
            SasBlob.check_blob_existence(PRIVATE_BLOB_URI)

    def test_list_blobs_in_container(self):
        blobs_list = SasBlob.list_blobs_in_container(
            PUBLIC_ZIPPED_CONTAINER_URI, limit=100)
        expected = sorted([
            'wcs_20200403_bboxes.json.zip', 'wcs_camera_traps.json.zip',
            'wcs_camera_traps_00.zip', 'wcs_camera_traps_01.zip',
            'wcs_camera_traps_02.zip', 'wcs_camera_traps_03.zip',
            'wcs_camera_traps_04.zip', 'wcs_camera_traps_05.zip',
            'wcs_camera_traps_06.zip', 'wcs_specieslist.csv',
            'wcs_splits.json'])
        self.assertEqual(blobs_list, expected)

    def test_generate_writable_container_sas(self):
        # until the private emulated account is able to work, skip this test
        self.skipTest('skipping private account tests for now')

        self.needs_cleanup = True
        new_sas_uri = SasBlob.generate_writable_container_sas(
            account_name=PRIVATE_ACCOUNT_NAME,
            account_key=PRIVATE_ACCOUNT_KEY,
            container_name=PRIVATE_CONTAINER_NAME,
            access_duration_hrs=1,
            account_url=PRIVATE_ACCOUNT_URI)
        self.assertTrue(isinstance(new_sas_uri, str))
        self.assertNotEqual(new_sas_uri, '')
        self.assertEqual(len(SasBlob.list_blobs_in_container(new_sas_uri)), 0)

    def test_upload_blob(self):
        self.needs_cleanup = True
        # uploading to a read-only public container without a SAS token yields
        # ResourceNotFoundError('The specified resource does not exist.')
        print('PUBLIC_CONTAINER_URI')
        with self.assertRaises(ResourceNotFoundError):
            SasBlob.upload_blob(PUBLIC_CONTAINER_URI,
                                blob_name='failblob', data='fail')

        # uploading to a public container with a read-only SAS token yields
        # HttpResponseError('This request is not authorized to perform this '
        #                   'operation using this permission.')
        print('PUBLIC_CONTAINER_URI_WITH_SAS')
        with self.assertRaises(HttpResponseError):
            SasBlob.upload_blob(PUBLIC_CONTAINER_URI_WITH_SAS,
                                blob_name='failblob', data='fail')

        # uploading to a private container without a SAS token yields
        # HttpResponseError('Server failed to authenticate the request. Make '
        #                   'sure the value of the Authorization header is '
        #                   'formed correctly including the signature.')
        print('PRIVATE_CONTAINER_URI')
        with self.assertRaises(HttpResponseError):
            SasBlob.upload_blob(PRIVATE_CONTAINER_URI,
                                blob_name=PRIVATE_BLOB_NAME, data='success')

        # until the private emulated account is able to work, skip this test
        # private_container_uri_with_sas = SasBlob.generate_writable_container_sas(
        #     account_name=PRIVATE_ACCOUNT_NAME,
        #     account_key=PRIVATE_ACCOUNT_KEY,
        #     container_name=PRIVATE_CONTAINER_NAME,
        #     access_duration_hrs=1,
        #     account_url=PRIVATE_ACCOUNT_URI)
        # blob_url = SasBlob.upload_blob(
        #     private_container_uri_with_sas,
        #     blob_name=PRIVATE_BLOB_NAME, data='success')
        # self.assertEqual(blob_url, PRIVATE_BLOB_URI)

    def test_get_blob_to_stream(self):
        output, props = SasBlob.get_blob_to_stream(PUBLIC_BLOB_URI)
        x = output.read()
        self.assertEqual(len(x), 376645)
        output.close()

        # see https://github.com/Azure/azure-sdk-for-python/issues/12563
        expected_properties = {
            'size': 376645,
            # 'name': PUBLIC_BLOB_NAME,
            # 'container': 'nacti-unzipped'
        }

        for k, v in expected_properties.items():
            self.assertEqual(props[k], v)

    def test_generate_blob_sas_uri(self):
        generated = SasBlob.generate_blob_sas_uri(
            container_sas_uri=PUBLIC_CONTAINER_URI,
            blob_name=PUBLIC_BLOB_NAME)
        self.assertEqual(generated, PUBLIC_BLOB_URI)

        generated = SasBlob.generate_blob_sas_uri(
            container_sas_uri=PUBLIC_CONTAINER_URI_WITH_SAS,
            blob_name=PUBLIC_BLOB_NAME)
        self.assertEqual(generated, PUBLIC_BLOB_URI_WITH_SAS)


if __name__ == '__main__':
    unittest.main()
