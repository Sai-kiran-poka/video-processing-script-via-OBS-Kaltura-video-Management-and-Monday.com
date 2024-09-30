# Video Processing and Notification Script

## Overview

This script automates the processing of video files, interacts with Monday.com and Kaltura APIs, and sends email notifications. It is designed to handle video uploads, update metadata, and notify users about the availability of their videos.

## Features

- **Integrates with Monday.com**: Retrieves board data to match and process video files.
- **Uploads Videos to Kaltura**: Handles video uploads and updates metadata in Kaltura.
- **Email Notifications**: Sends notifications to users regarding their video status.
- **File Management**: Moves and renames video files based on session data.

## Setup

1. **Create a `.env` file**:
   
   The `.env` file should contain your environment variables. Example:
   ```dotenv
   MONDAY_API_KEY=your_monday_api_key
   KALTURA_PARTNER_ID=your_kaltura_partner_id
   KALTURA_ADMIN_SECRET=your_kaltura_admin_secret
   KALTURA_USER_ID=your_kaltura_user_id
   KALTURA_SERVICE_URL=your_kaltura_service_url
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=your_smtp_port
   SMTP_USERNAME=your_smtp_username
   SMTP_PASSWORD=your_smtp_password
   SMTP_FROM_ADDRESS=your_smtp_from_address

2. **Update Directory Paths file**:
 # Directories
    # Directories
directory_to_watch = 'C:\\OBS-Files'           # Directory to watch for new video files
directory_to_processing = 'C:\\OBS-Processing' # Directory for files during processing
directory_to_recordings = 'C:\\OBS-Recordings' # Directory for processed files


3. **Update Monday.com Board ID in python Script**:
  query = """
  {
    boards(ids: [your_board_id]) {
        ...
    }
  } 
   """

4. **Update Default Email Address in python Script**:
# Default email if MIDAS ID does not have an account
  DEFAULT_EMAIL = "your_default_email"


5. **Create a Virtual Environment**:
 # run below commands in terminal 
python -m venv venv
venv\Scripts\activate

6. **Install the packages**:
 # run below commands in terminal 
  pip install -r requirements.txt

