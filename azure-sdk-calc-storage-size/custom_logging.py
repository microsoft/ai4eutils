#%% Imports

import os
import logging

from datetime import datetime
from pytz import timezone, utc


#%% Class and function definitions

def custom_time():

    utc_dt = utc.localize(datetime.utcnow())
    US_pacific_time_zone = timezone("US/Pacific")
    converted = utc_dt.astimezone(US_pacific_time_zone)
    return converted.timetuple()

class CustomLogging:

    def __init__(self):

        date_part = datetime.now().strftime('%m_%d_%Y_%H_%M_%S')

        # Log file directories
        self.root_log_direc = "logs"
        self.debug_log_direc = self.root_log_direc + "/debug_logs"
        self.info_log_direc = self.root_log_direc + "/info_logs"

        # Log file names
        self.debug_log = "logs/debug_logs/debug_"+ date_part + ".log" 
        self.storage_info_log = "logs/info_logs/storage_sizes " + date_part + ".log"
        self.blob_container_info_log = "logs/info_logs/blob_container_and_blob_sizes _"+ date_part + ".log"

        self.logformatter = logging.Formatter('%(message)s')

        self.create_log_directories()

        self.debug_logger = self.setup_logger('info_log', self.debug_log,  self.logformatter, level=logging.DEBUG)
        self.storage_info_logger = self.setup_logger('storage_size_log', self.storage_info_log, self.logformatter)
        self.blob_container_info_logger = self.setup_logger('blob_container_size_log', self.blob_container_info_log, self.logformatter)

        self.csv_storage_size_headers = 'entry type, storage account name, size, size (friendly)'
        self.csv_blob_container_size_headers = 'entry type, entity name, size, size (friendly)'

        self.add_headers()


    def create_log_directories(self):

        if not os.path.exists(self.root_log_direc):
            os.mkdir(self.root_log_direc)

        if not os.path.exists(self.debug_log_direc):
            os.mkdir(self.debug_log_direc)
        
        if not os.path.exists(self.info_log_direc):
            os.mkdir(self.info_log_direc)


    def setup_logger(self, name, log_file, formatter, level=logging.INFO):
        
        handler = logging.FileHandler(log_file, mode='a', encoding=None, delay=False)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)

        return logger
        
    
    def add_headers(self):
        
        self.storage_info_logger.info(self.csv_storage_size_headers)
        self.blob_container_info_logger.info(self.csv_blob_container_size_headers)
      
        
    def log_error(self, message):
        
        self.debug_logger.error(message)


    def log_debug_info(self, message):
        
        self.debug_logger.debug(message)
   
    
    def log_storage_info(self, message):
    
        self.storage_info_logger.info(message)
   
    
    def log_blob_container_info(self, message):
        
        self.blob_container_info_logger.info(message)

