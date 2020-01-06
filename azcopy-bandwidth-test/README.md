# Introduction 

Uploads a file to a storage account using a SAS URL and returns the upload bandwidth based on elapsed time and bytes transferred.

# How to run

```
python azcopy_upload_test.py 'https://sas_url' --path 'sample.txt' --size 1 --page_blob
````

Description of parameters
* sas_url: SAS URL of the blob container starting with https, this argument is required
* path (optional): Path of file that is to be uploaded; if omitted, a file will be created
* size (optional): Size of the file in GB, which will be used to create a sample file (default is 8GB)
* page_blob (optional): Specifies that the target storage uses page blobs (rather than block blobs)
