#%% Constants and imports

from msrestazure.azure_active_directory import AADTokenCredentials
from azure.mgmt.resource import SubscriptionClient

import adal
import datetime

from pytz import timezone, utc

authority_host_uri = 'https://login.microsoftonline.com'
resource_uri = 'https://management.core.windows.net/'
device_login_url = 'https://microsoft.com/devicelogin'


#%% Authentication and utility functions

def authenticate_device_code(AuthenticationInfo):
    """
    Authenticate the end-user using device auth.
    """
    authority_uri = authority_host_uri + '/' + AuthenticationInfo.tenant
    
    context = adal.AuthenticationContext(authority_uri, api_version=None)
    code = context.acquire_user_code(resource_uri, AuthenticationInfo.client_id)
    print(code['message'])
    
    # This doesn't work in a console environment
    # webbrowser.open(device_login_url + '?input='+ code['user_code'], new=2)

    print('To authenticate, open a browser to this URL:\n{}'.format(device_login_url + '?input='+ code['user_code']))
    
    mgmt_token = context.acquire_token_with_device_code(resource_uri, code, AuthenticationInfo.client_id)
    credentials = AADTokenCredentials(mgmt_token, AuthenticationInfo.client_id)

    return credentials


def get_subscription_id(credentials):
    
    first_run = True
    subscription_id = None
    name = ""
    
    while subscription_id is None:
        
        if first_run:
            name = input("Enter subscription name:")
            print(name)
            subscription_id = find_subscription_by_name(
                                                 name.strip(), 
                                                 credentials)
        
        else:
            print("\nCould not find subscription with name: \n" + name)
            name = input("\n Try again. Enter subscription name:")
            subscription_id = find_subscription_by_name(
                                                    name.strip(), 
                                                    credentials)

        first_run = False

    return subscription_id    


def find_subscription_by_name(sub_name, credentials):

    subscriptionClient = SubscriptionClient(credentials)
    subscriptions = subscriptionClient.subscriptions.list()
    if subscriptions is not None:
        for sub in subscriptions:
            if sub_name.lower() == sub.display_name.lower():
                return sub.subscription_id
    return None


def custom_time():

    utc_dt = utc.localize(datetime.utcnow())
    US_pacific_time_zone = timezone("US/Pacific")
    converted = utc_dt.astimezone(US_pacific_time_zone)
    return converted.timetuple()

