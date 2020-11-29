#%% Constants and imports

from msrestazure.azure_active_directory import AADTokenCredentials
from azure.mgmt.resource import SubscriptionClient

import adal

authority_host_uri = 'https://login.microsoftonline.com'
resource_uri = 'https://management.core.windows.net/'
device_login_url = 'https://microsoft.com/devicelogin'


#%% Authentication and utility functions

def authenticate_client_key(authenticationInfo):
    """
    Authenticate using service principal w/ key.
    """
    authority_uri = authority_host_uri + '/' + authenticationInfo.tenant
    app_id = authenticationInfo.app_id
    app_secret = authenticationInfo.app_secret

    context = adal.AuthenticationContext(authority_uri, api_version=None)
    mgmt_token = context.acquire_token_with_client_credentials(resource_uri, app_id, app_secret)
    credentials = AADTokenCredentials(mgmt_token, app_id)

    return credentials


def authenticate_device_code(authenticationInfo):
    """
    Authenticate the end-user using device auth.
    """
    authority_uri = authority_host_uri + '/' + authenticationInfo.tenant
    
    context = adal.AuthenticationContext(authority_uri, api_version=None)
    code = context.acquire_user_code(resource_uri, authenticationInfo.client_id)
    print(code['message'])
        
    # This doesn't work in a console environment
    # webbrowser.open(device_login_url + '?input='+ code['user_code'], new=2)
    
    print('To authenticate, open a browser to this URL:\n{}'.format(device_login_url + '?input='+ code['user_code']))
    
    mgmt_token = context.acquire_token_with_device_code(resource_uri, code, authenticationInfo.client_id)
    credentials = AADTokenCredentials(mgmt_token, authenticationInfo.client_id)

    return credentials


def get_subscription_id(credentials):
    
    first_run = True
    subscription_id = None
    name = ""
    
    while subscription_id is None:
        
        if(first_run):
            name = input("Enter subscription name:")
            subscription_id = find_subscription_by_name(
                                                 name.strip(), 
                                                 credentials)
        
        else:
            print("\nCould not find subscription with name: \n" + name)
            name = input("\n Try again. Enter subscription name :")
            subscription_id = find_subscription_by_name(
                                                    name.strip(), 
                                                    credentials)

        first_run = False

    return subscription_id    


def find_subscription_by_name(sub_name, credentials):

    subscriptionClient = SubscriptionClient(credentials)
    subscriptions = subscriptionClient.subscriptions.list()
    if(subscriptions is not None):
        for sub in subscriptions:
            if(sub_name.lower() == sub.display_name.lower()):
                return sub.subscription_id
    return None



