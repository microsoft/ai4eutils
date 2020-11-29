#%% Constants and imports

import utils
import datetime
import pandas as pd
import humanfriendly
import math

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.storage import StorageManagementClient

from enum import Enum

class Authentication:

    # This refers to the on.microsoft.com directory, change this to enumerate alternative
    # directories.
    tenant = '72f988bf-86f1-41af-91ab-2d7cd011db47'
    
    # This is the client ID for the Azure CLI
    client_id = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'

METRICS_NOT_AVAILABLE = float('nan')

class Metric_type(Enum): 

    blob_capacity = 1
    fileshare_capacity = 2


#%% Classes and functions

def get_used_avg_blob_capacity(credentials,subscription_id):
    
    resource_client = ResourceManagementClient(credentials, subscription_id)
    storage_client = StorageManagementClient(credentials, subscription_id)
    
    lst = []
    count = 0
    resource_groups = resource_client.resource_groups.list()

    for group in resource_groups:        
        
        storage_accounts = storage_client.storage_accounts.list_by_resource_group(group.name)
        
        for storage_account in storage_accounts:

            print("Reading metric data from storage account: " + storage_account.name)
            count += 1
            
            blob_size = get_metric_data_capacity(group.name, storage_account.name, 
                                        subscription_id, Metric_type.blob_capacity)
            file_size = get_metric_data_capacity(group.name, storage_account.name, 
                                        subscription_id, Metric_type.fileshare_capacity)
            
            total_size = blob_size + file_size
            
            if math.isnan(total_size):
                total_size_friendly = ''
            else:
                total_size_friendly = humanfriendly.format_size(total_size)
            
            lst.append([storage_account.name, group.name, blob_size, file_size, total_size, total_size_friendly])
            
    print("Total number of storage accounts: "+ str(count))
    cols = ['Storage account', 'Resource group', 'Blob capacity', 'File capacity', 'Total capacity', 'Total capacity (friendly)']
    df = pd.DataFrame(lst, columns=cols)
    
    file_name = 'metrics_' + datetime.datetime.now().strftime('%m-%d-%y-%H%M%S') + '.csv'
    df.to_csv(file_name, header=cols, index=False)
    print("\n")
    print("Metrics saved to file: " + file_name)
    return file_name
        

def get_metric_data_capacity(resource_group_name, storage_account_name, subscription_id, type):
    
    client = MonitorManagementClient(credentials, subscription_id)

    today = datetime.datetime.utcnow().date()
    yesterday = today - datetime.timedelta(days=1)

    resource_id = (
            "subscriptions/{}/"
            "resourceGroups/{}/"
            "providers/Microsoft.Storage/storageAccounts/{}/{}")
    
    metrics_data = None
        
    if (type == Metric_type.blob_capacity):
        
        resource_id = resource_id.format(subscription_id, 
            resource_group_name, storage_account_name, 'blobServices/default')
        
        metrics_data = client.metrics.list(
            resource_id,
            timespan="{}/{}".format(yesterday, today),
            interval='PT1H',
            metric='Blob capacity',
            aggregation='Average')

    if (type == Metric_type.fileshare_capacity):    
            
        resource_id = resource_id.format(subscription_id, 
        resource_group_name, storage_account_name, 'fileServices/default')
        
        metrics_data = client.metrics.list(
            resource_id,
            timespan="{}/{}".format(yesterday, today),
            interval='PT1H',
            metric='File capacity',
            aggregation='Average')
    
    if(metrics_data.value is None):
        
        return METRICS_NOT_AVAILABLE
    
    for item in metrics_data.value:
        
        for item in item.timeseries:
            if(len(item.data) > 0):
                data = item.data[-1]
                if(data.average is not None):
                    return data.average
                else:
                    return METRICS_NOT_AVAILABLE

    return METRICS_NOT_AVAILABLE     

# ... def get_metric_data_capacity
    

#%% Command-line driver
    
if __name__ == '__main__':

     #%%
     
     auth = Authentication()
     credentials = utils.authenticate_device_code(auth)
     
     subscription_id =  utils.get_subscription_id(credentials)
    
     file_name = get_used_avg_blob_capacity(credentials,subscription_id)
     print('Wrote results to {}'.format(file_name))
     
