import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from typing import List, Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setup the logger
logger = logging.getLogger('DriveMonitor')
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler('drive_monitor.log')
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter and set it for both handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class DriveMonitor:
    CREDENTIALS_FILE = './credentials.json'
    TOKEN_FILE = 'token.pickle'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self):
        self.creds = self._authenticate()
        self.service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self):
        creds = None
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        return creds

    def is_file_open_for_everyone(self, file_id: str) -> bool:
        try:
            file = self.service.files().get(fileId=file_id, fields="id, name, permissions").execute()
            permissions = file.get('permissions', [])
            public_access = any(p['type'] == 'anyone' for p in permissions)
            return public_access
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return False

    def is_folder_open_for_everyone(self, folder_id: str) -> bool:
        try:
            folder = self.service.files().get(fileId=folder_id, fields="id, name, permissions").execute()
            permissions = folder.get('permissions', [])
            public_access = any(p['type'] == 'anyone' for p in permissions)
            return public_access
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return False

    def remove_anyone_can_access_permissions(self, file_id: str) -> None:
        try:
            permissions = self.service.permissions().list(fileId=file_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('type') == 'anyone':
                    self.service.permissions().delete(fileId=file_id, permissionId=permission.get('id')).execute()
                    logger.info(f'Changed sharing settings to private for file ID: {file_id}')
        except HttpError as error:
            logger.error(f'An error occurred: {error}')

    def get_parent_folder_id(self, file_id: str) -> str | None:
        try:
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            parents = file.get('parents', [])
            return parents[0] if parents else None
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return None

    def create_file(self, ignore_default_visibility: bool):
        try:
            file_metadata = {
                'name': 'Test File',
                'mimeType': 'application/vnd.google-apps.document'
            }
            file = self.service.files().create(
                body=file_metadata,
                fields='id, permissions',
                ignoreDefaultVisibility=ignore_default_visibility
            ).execute()
            return file
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return None

    def _compare_file_permissions_between_file_with_default_visibility_and_without(self,
                                                                                   file_id_with_default_visibility: str,
                                                                                   file_id_no_default_visibility: str):
        try:
            file1 = self.service.files().get(fileId=file_id_with_default_visibility, fields='permissions').execute()
            file2 = self.service.files().get(fileId=file_id_no_default_visibility, fields='permissions').execute()

            permissions1 = file1.get('permissions', [])
            permissions2 = file2.get('permissions', [])

            logger.debug(f'Permissions for file1 (ignoreDefaultVisibility=False): {permissions1}')
            logger.debug(f'Permissions for file2 (ignoreDefaultVisibility=True): {permissions2}')

            if permissions2:
                permission_id = permissions2[0].pop('id')
                logger.info(
                    f'The permission ID from file2 (ignoreDefaultVisibility=True) that should match in file1: {permission_id}')
                new_permissions = []
                for permission in permissions1:
                    if permission.get('id') != permission_id:
                        new_permissions.append(permission)

                return new_permissions

        except HttpError as error:
            logger.error(f'An error occurred: {error}')

    def get_all_files(self, interval: int) -> List[Any]:
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(seconds=interval)
        formatted_time = one_minute_ago.strftime('%Y-%m-%dT%H:%M:%S')
        page_token = ""
        combined_file_list = []
        while page_token is not None:
            file_list_response = self.service.files().list(
                q=f"modifiedTime > '{formatted_time}' and mimeType != 'application/vnd.google-apps.folder'",
                spaces='drive',
                fields='nextPageToken, files(id, name)', pageSize=100, pageToken=page_token).execute()
            combined_file_list.extend(file_list_response.get('files', []))
            page_token = file_list_response.get('nextPageToken')

        return combined_file_list

    def monitor_drive(self, interval: int) -> None:
        logger.info(f"Starting to monitor every {interval} seconds")
        while True:
            files = self.get_all_files(interval)
            for file in files:
                file_id = file.get('id')
                file_name = file.get('name')
                if self.is_file_open_for_everyone(file_id):
                    parent_folder_id = self.get_parent_folder_id(file_id)
                    if parent_folder_id and self.is_folder_open_for_everyone(parent_folder_id):
                        self.remove_anyone_can_access_permissions(file_id)
                        logger.info(f'File: {file_name} (ID: {file_id}) was a public file and is now private.')
                    else:
                        logger.info(
                            f'File: {file_name} (ID: {file_id}) is a public file'
                            f' but in a private folder, so not changing permissions')
                else:
                    logger.info(f'File: {file_name} (ID: {file_id}) is a private file')

            time.sleep(interval)  # Check every minute for new files

    def get_default_sharing_settings(self):
        logger.info('Creating two test files to compare default sharing settings...')
        file_with_default_visibility = self.create_file(ignore_default_visibility=False)
        file_no_default_visibility = self.create_file(ignore_default_visibility=True)
        if file_with_default_visibility and file_no_default_visibility:
            new_permissions = self._compare_file_permissions_between_file_with_default_visibility_and_without(
                file_with_default_visibility['id'], file_no_default_visibility['id'])
            # Clean up by deleting the test files
            self.service.files().delete(fileId=file_with_default_visibility['id']).execute()
            self.service.files().delete(fileId=file_no_default_visibility['id']).execute()

            return new_permissions
        else:
            logger.error('Failed to create test files for comparison.')

        return []


if __name__ == '__main__':
    drive_monitor = DriveMonitor()
    logger.info(f"default sharing settings {drive_monitor.get_default_sharing_settings()}")
    drive_monitor.monitor_drive(60)
