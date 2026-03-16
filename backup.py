import os
import tarfile
import datetime
import shutil
from cryptography.fernet import Fernet
import logging

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
# In production, this should be an environment variable
BACKUP_KEY = os.environ.get('BACKUP_KEY', Fernet.generate_key().decode())

# Setup logging
logging.basicConfig(filename='backup.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'inventory_backup_{timestamp}.tar.gz'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # 1. Create Tar archive of DB and Media
        with tarfile.open(backup_path, "w:gz") as tar:
            if os.path.exists(DB_FILE):
                tar.add(DB_FILE, arcname='db.sqlite3')
            if os.path.exists(MEDIA_DIR):
                tar.add(MEDIA_DIR, arcname='media')
        
        logging.info(f"Archive created: {backup_filename}")
        
        # 2. Encrypt the archive
        fernet = Fernet(BACKUP_KEY.encode())
        with open(backup_path, 'rb') as f:
            data = f.read()
        
        encrypted_data = fernet.encrypt(data)
        
        encrypted_path = backup_path + '.enc'
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
            
        logging.info(f"Backup encrypted: {encrypted_path}")
        
        # 3. Cleanup original archive
        os.remove(backup_path)
        
        # 4. Simulation of Cloud Upload
        # Here you would use boto3 for S3 or google-api-python-client for Drive
        cloud_sim_dir = os.path.join(BACKUP_DIR, 'cloud_simulation')
        if not os.path.exists(cloud_sim_dir):
            os.makedirs(cloud_sim_dir)
        shutil.copy(encrypted_path, cloud_sim_dir)
        
        logging.info("Backup uploaded to cloud (simulation).")
        print(f"Backup successful: {encrypted_path}")
        print(f"IMPORTANT: Save this key to restore backups: {BACKUP_KEY}")
        
    except Exception as e:
        logging.error(f"Backup failed: {str(e)}")
        print(f"Backup failed: {e}")

if __name__ == '__main__':
    create_backup()
