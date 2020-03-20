#
# back_up_blob_containers.py
#
# Generate azcopy commands to sync containers from a source to a destination SA,
# creating and (optionally) removing containers at the destination that 
# exist/don't exist at the source.
#
# Essentially this is extending azcopy sync functionality to the storage account
# level.
#

#%% Constants and imports

from azure.storage.blob import BlobServiceClient

source_account_name = 'mysource'
target_account_name = 'mytarget'

source_account_url_blob = 'https://' + source_account_name + '.blob.core.windows.net'
target_account_url_blob = 'https://' + target_account_name + '.blob.core.windows.net'

source_sas_token = '?sv=...'
target_sas_token = '?sv=...'
    
output_file_base = r'd:\temp\sync_containers_'
output_file = output_file_base + source_account_name + '_' + target_account_name + '.sh'
delete_extra_containers = True


#%% Support functions

# https://gist.github.com/gurunars/4470c97c916e7b3c4731469c69671d06
def confirm():
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("OK to continue [Y/N]? ").lower()
    return answer == "y"


#%% Create the clients

source_blob_service_client = BlobServiceClient(account_url=source_account_url_blob, credential=source_sas_token)
target_blob_service_client = BlobServiceClient(account_url=target_account_url_blob, credential=target_sas_token)


#%% List source and destination containers

source_container_iter = source_blob_service_client.list_containers(include_metadata=True)
target_container_iter = target_blob_service_client.list_containers(include_metadata=True)

source_containers = []
target_containers = []

print('Source containers:')
for container in source_container_iter:
    source_containers.append(container)    
    print(container['name'], container['metadata'])

print('\nTarget containers:')
for container in target_container_iter:
    target_containers.append(container)
    print(container['name'], container['metadata'])
    

#%% Find missing/extra containers

source_container_names = list([c['name'] for c in source_containers])
target_container_names = list([c['name'] for c in target_containers])
                
missing_containers = []
for container in source_container_names:
    if container not in target_container_names:
        missing_containers.append(container)

extra_containers = []
for container in target_container_names:
    if container not in source_container_names:
        extra_containers.append(container)
        
print('Missing containers:')        
for c in missing_containers:
    print(c)
    
print('\nExtra containers:')        
for c in extra_containers:
    print(c)
    
    
#%% Delete extra containers
    
if delete_extra_containers:    
    # c = extra_containers[0] 
    for c in extra_containers:
        print('Delete container {} from storage account {}?'.format(
                c,target_blob_service_client.account_name))
        if confirm():   
            target_blob_service_client.delete_container(c)

    
#%% Create missing containers

# c = missing_containers[0]
for c in missing_containers:    
    print('Creating container {} in storage account {}'.format(
            c,target_blob_service_client.account_name))
    target_blob_service_client.create_container(c)
    
    
#%% Generate azcopy commands

azcopy_commands = []

# c = source_container_names[0]
for c in source_container_names:
    
    cmd = 'azcopy sync "'
    cmd += source_account_url_blob + '/' + c + '/' + source_sas_token
    cmd += '" "'
    cmd += target_account_url_blob + '/' + c + '/' + target_sas_token
    cmd += '" --delete-destination=True --log-level=NONE'
    
    azcopy_commands.append(cmd)

# Debug by testing on a single container
if False:
    i_command = -2
    import clipboard
    clipboard.copy(azcopy_commands[i_command])
    print(azcopy_commands[i_command])
    azcopy_commands = [ azcopy_commands[i_command] ]


#%% Write azcopy commands out to a shell script
    
with open(output_file,'w',newline='') as f:
    for cmd in azcopy_commands:
        f.write(cmd + '\n')

