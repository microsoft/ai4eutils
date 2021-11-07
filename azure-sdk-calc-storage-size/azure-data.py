#%% Imports

# import os; os.chdir(r'C:\git\ai4eutils\azure-sdk-calc-storage-size')
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient
from custom_logging import CustomLogging
from enum import Enum

import utils
import datetime
import humanfriendly


#%% Auth and storage computation classes

class SizeOptions:

    account_names = None
    container_names = None
    log_individual_blobs = True


class Authentication:

    # This refers to the on.microsoft.com directory, change this to enumerate alternative
    # directories.
    tenant = '72f988bf-86f1-41af-91ab-2d7cd011db47'

    # This is the client ID for the Azure CLI
    client_id = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'


class Log_type(Enum):

    programstart = 1
    programstop = 2
    debug = 3
    storage_info = 4
    blob_info = 5
    container_info = 6


class AzureStorageSize:

    def __init__(self, credentials, subscription_id, log):

        self.credentials = credentials
        self.subscription_id = subscription_id
        self.resource_client = ResourceManagementClient(self.credentials, self.subscription_id)
        self.storage_client = StorageManagementClient(self.credentials, self.subscription_id)
        self.log = log


    def get_all_storage_accounts(self):

        storage_accounts = self.storage_client.storage_accounts.list()

        return storage_accounts


    def get_storage_account_resource_group(self, resource_id):

        temp = resource_id.split("/")
        resource_group = temp[4]

        return resource_group


    def get_storage_account_keys(self, resource_group_name, storage_account_name):

        storage_keys = self.storage_client.storage_accounts.list_keys(resource_group_name, storage_account_name)
        storage_keys = {v.key_name: v.value for v in storage_keys.keys}

        return storage_keys


    def get_blob_containers_by_storage_account(self, storage_account_name, account_key):

        blob_service = BlobServiceClient(
            account_url=f'{storage_account_name}.blob.core.windows.net',
            credential=account_key)
        containers = blob_service.list_containers()

        return containers


    def get_all_blobs_by_blob_container_name(self, storage_account_name, account_key, container_name):

        container_client = ContainerClient(
            account_url=f'{storage_account_name}.blob.core.windows.net',
            container_name=container_name, credential=account_key)
        blobs = container_client.list_blobs()

        return blobs


    def log_info(self, message, type):

        print(message)

        if(type == Log_type.programstart):

            self.log.log_debug_info(message)

        if(type == Log_type.programstop):

            self.log.log_debug_info(message)
            self.log.log_storage_info(message)
            self.log.log_blob_container_info(message)

        if(type == Log_type.debug):

            self.log.log_debug_info(str(datetime.datetime.now()) + " " + message)

        if(type == Log_type.storage_info):

            self.log.log_storage_info(message)

        if(type == Log_type.blob_info):

            self.log.log_blob_container_info(message)


    def get_storage_size(self, options=None):

        try:

            if options is None:

                options = SizeOptions()

            storage_accounts = self.get_all_storage_accounts()
            count = 0

            for storage_account in storage_accounts:

                storage_account_name = storage_account.name

                if options.account_names is not None and storage_account_name not in options.account_names:

                    print("Skipping storage account: " + storage_account_name , Log_type.debug)
                    continue

                count += 1
                self.log_info("\nProcessing storage account: " + storage_account_name , Log_type.debug)

                total_account_size = 0
                
                resource_group_name = self.get_storage_account_resource_group(storage_account.id)
                account_key = self.get_storage_account_keys(resource_group_name, storage_account_name)['key1']
                blob_containers = self.get_blob_containers_by_storage_account(storage_account_name, account_key)

                for container in blob_containers:

                    container_name = container.name

                    if options.container_names is not None and container_name not in options.container_names:

                        print("Skipping container: " + container_name, Log_type.debug)
                        continue

                    self.log_info("Reading size for container: " +  container_name, Log_type.debug)

                    total_blob_container_size = 0

                    blobs = self.get_all_blobs_by_blob_container_name(storage_account_name,
                        account_key, container_name)

                    for blob in blobs:

                        with BlobClient(
                                account_url=f'{storage_account_name}.blob.core.windows.net',
                                container_name=container.name, blob_name=blob.name,
                                credential=account_key) as blob_client:
                            size = blob_client.get_blob_properties().size

                        total_blob_container_size +=  size
                        total_account_size +=  size

                        
                        if options.log_individual_blobs:
                            
                            blob_size_str = humanfriendly.format_size(size)                        
                            message = "{}, {}, {}, {}".format("blob_size", blob.name, str(size), blob_size_str)
                            self.log_info(message, Log_type.blob_info)

                    # ...for each blob
                    
                    blob_container_size_str = humanfriendly.format_size(total_blob_container_size)
                    message = "{}, {}, {}, {}".format("blob_container_total", container_name,
                                                                            str(total_blob_container_size),
                                                                            blob_container_size_str)
                    self.log_info(message, Log_type.container_info)

                # ...for each container
                
                total_account_size_str = humanfriendly.format_size(total_account_size)

                self.log_info("Number of storage accounts processed: " + str(count), Log_type.debug)

                message = "{}, {}, {}, {}".format("storage_total",storage_account_name, str(total_account_size), total_account_size_str)
                self.log_info(message, Log_type.storage_info)

        except Exception as e:

            print(str(e))
            self.log.log_error(str(e))


#%% Command-line driver

if __name__ == '__main__':

    #%%

    options = SizeOptions()
    # options.account_names = ['wildlifeblobssc']
    # options.log_individual_blobs = False
    
    log = CustomLogging()

    auth = Authentication()

    credentials = utils.authenticate_device_code(auth)

    #authenticate using azure registered app
    #credentials = authenticate_client_key = utils.authenticate_client_key(auth)

    subscription_id = utils.get_subscription_id(credentials)

    print('Writing logps to:\n{}\n{}\n{}\n\n'.format(
            log.debug_log, log.blob_container_info_log, log.storage_info_log))

    azure_st = AzureStorageSize(credentials, subscription_id, log)
    azure_st.log_info("Program started on: " + str(datetime.datetime.now()) + "\n", Log_type.debug)
    azure_st.get_storage_size(options)
    azure_st.log_info("\n\nProgram ended on: " + str(datetime.datetime.now()) + "\n", Log_type.debug)

    print('Finished writing logs to:\n{}\n{}\n{}\n'.format(log.debug_log,
          log.blob_container_info_log,log.storage_info_log))
