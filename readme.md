# DriveMonitor

## Overview

This Python script monitors Google Drive for files that are publicly accessible and makes them private if they are located in publicly accessible folders. It also includes functionality to compare the default sharing settings of files created with different visibility settings.

### Requirements

- Python 3.11
- `google-api-python-client`
- `google-auth-httplib2`
- `google-auth-oauthlib`

### Installation

1. **Create and Install from `requirements.txt`**:
    - Install the required packages using pip:
      ```sh
      pip install -r requirements.txt
      ```

### Usage

1. **Setup Credentials**: OAuth 2.0 credentials JSON file (`credentials.json`) should be in the same directory as the script, the file should be in gmail.

2. **Run the Script**: The first time you run the script, a browser window will open for you to log in and authorize the application. This will create a `token.pickle` file for subsequent runs.
3. **Insert Credentials**: when the popup to login to gmail appears, insert credentials given via the email
4. **Run the program**: as showed here:

    ```sh
    python drive_monitor.py
    ```

5. **Monitor Drive**: The script will start monitoring your Google Drive and adjust sharing settings as necessary.
6. **Available Changes**: You may comment out the monitor or the default sharing settings at the end of the file, or change the interval which by default is `60 seconds`

**Caveats**:
- The script has not been tested for default sharing settings due to lack of access to specific configurations. when I tested, I added permissions in the middle of the program in order to mimic the behavior.
- Default sharing settings comparison might be more elegantly handled with admin permissions in Google Workspace mode.
- The script currently creates comparison test files in the main drive but should ideally create them in a system folder or a dedicated testing folder.

### Security Considerations

The `allowFileDiscovery` flag makes files publicly searchable. by default, it is False, Care must be taken to understand the implications of this setting, especially in shared or domain-accessible environments
After Investigating, I understood that this flag was previously True, so then publicly accessible files might be indexed by search engines, potentially exposing sensitive information. More research is needed to understand the full implications of this setting.
However, by using specific Google search queries, We can see those file. For example, you can find publicly available files with may contain sensitive information this search query: [Google Search Query Example](https://www.google.com/search?q=%22username%22+%22password%22+%22root%22+site%3Adocs.google.com&sca_esv=d274f197743d8e0a&sca_upv=1&biw=1278&bih=1270&sxsrf=ADLYWIK1DMXvPh4KvqY4YJfetl7XH3sx1g%3A1719171542203&ei=1nl4ZuGLDNKlkdUPpNe5uAE&ved=0ahUKEwjhztKIvfKGAxXSUqQEHaRrDhcQ4dUDCA8).