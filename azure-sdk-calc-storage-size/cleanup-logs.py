import os

def delete_old_logs():

        log_path = "logs"
        error = False
        for root, dirs, files in os.walk(log_path):
            for file in files:
                path = os.path.join(root, file)
                try:
                    os.remove(path)
                except Exception as e:
                    print("Could not delete file: " + path)
                    print(str(e))
        if(error):
            print("Logs deleted, but there were some errors")
        else:
            print("All logs where deleted successfully")

if __name__ == '__main__':
    
    delete_old_logs()
