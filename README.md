# Overview

Shared utilities developed by the Microsoft AI for Earth team

The general convention in this repo is that users who want to consume these utilities will add the top-level path of the repo to their Python path, so it's okay to assume that other packages/modules within the repo are available.  The "scrap" directory can be used for standalone, one-time-use scripts that you might otherwise have emailed to someone.

# Contents

- [path_utils.py](path_utils.py): Miscellaneous useful utils for path manipulation, things that could *almost* be in os.path, but aren't.

- [matlab_porting_tools.py](matlab_porting_tools.py): A few ported Matlab functions that makes it easier to port other, larger Matlab functions to Python.

- [write_html_image_list.py](write_html_image_list.py): Given a list of image file names, writes an HTML file that shows all those images, with optional one-line headers above each.

- [sas_blob_utils.py](sas_blob_utils.py): Helper functions for dealing with Shared Access Signatures (SAS) tokens
for Azure Blob Storage.

- [TF_OD_API](TF_OD_API): A Dockerfile and a script to prepare a Docker image for use with the [TensorFlow Object Detection API](https://github.com/tensorflow/models/tree/master/research/object_detection).

- [gDrive_download.py](gDrive_download.py): Semi-automatic script for bulk download from shared Google Drives using the gDrive Python SDK.

- [azure-sdk-calc-storage-size](azure-sdk-calc-storage-size): Script for recursively computing the size of all blobs and files in an Azure subscription.

- [azure-metrics-calc-storage-size](azure-metrics-calc-storage-size): Script for computing the total size of all storage accounts in an Azure subscription (using Azure Metrics).

- [ai4e_azure_utils.py](ai4e_azure_utils.py): Functions for interacting with the Azure Storage SDK

- [ai4e_web_utils.py](ai4e_web_utils.py): Functions for interacting with http requests

- [geospatial](geospatial): Classes and utility functions for processing geospatial data for machine learning applications


# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
