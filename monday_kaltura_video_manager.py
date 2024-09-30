import os
import re
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from KalturaClient import *
from KalturaClient.Plugins.Core import *
import smtplib
from email.mime.text import MIMEText

# Load environment variables from .env file
load_dotenv()

# Monday API key
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")

# Kaltura API details
KALTURA_PARTNER_ID = os.getenv("KALTURA_PARTNER_ID")
KALTURA_ADMIN_SECRET = os.getenv("KALTURA_ADMIN_SECRET")
KALTURA_USER_ID = os.getenv("KALTURA_USER_ID")
KALTURA_SERVICE_URL = os.getenv("KALTURA_SERVICE_URL")






# Default email if MIDAS ID does not have an account
DEFAULT_EMAIL = "spoka001@odu.edu"







# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Directories
directory_to_watch = 'C:\\OBS-Files'
directory_to_processing = 'C:\\OBS-Processing'
directory_to_recordings = 'C:\\OBS-Recordings'

os.makedirs(directory_to_watch, exist_ok=True)
os.makedirs(directory_to_processing, exist_ok=True)
os.makedirs(directory_to_recordings, exist_ok=True)

# Initialize Kaltura client
def init_kaltura_client():
    logging.info(f"Kaltura Service URL: {KALTURA_SERVICE_URL}")
    logging.info(f"Kaltura Partner ID: {KALTURA_PARTNER_ID}")
    logging.info(f"Kaltura User ID: {KALTURA_USER_ID}")

    config = KalturaConfiguration(KALTURA_PARTNER_ID)
    config.serviceUrl = KALTURA_SERVICE_URL
    client = KalturaClient(config)

    try:
        ks = client.session.start(KALTURA_ADMIN_SECRET, KALTURA_USER_ID, KalturaSessionType.ADMIN, KALTURA_PARTNER_ID)
        client.setKs(ks)
        logging.info("Kaltura session initialized successfully.")
        return client
    except Exception as e:
        logging.error(f"Error initializing Kaltura client: {e}")
        raise

# Check if a Kaltura user with the given email exists
def get_user_by_email(client, email):
    try:
        user = client.user.getByEmail(email)
        logging.info(f"User found in Kaltura: {email}")
        return user
    except Exception as e:
        logging.warning(f"User not found: {email}. Using default email.")
        return None

# Update the admin owner of the Kaltura video entry
def update_kaltura_admin_owner(client, entry_id, admin_email):
    try:
        # Create a new media entry object to update the ownerId
        media_entry = KalturaMediaEntry()
        media_entry.ownerId = admin_email  # Set the new owner email as the ownerId

        # Update the media entry with the new ownerId
        result = client.media.update(entry_id, media_entry)
        logging.info(f"Admin owner updated to {admin_email} for entry ID: {entry_id}")
    except Exception as e:
        logging.error(f"Error updating admin owner: {str(e)}")


# Upload video to Kaltura and assign admin owner
def upload_video_to_kaltura(client, file_path, video_title, midas_email, original_filename, renamed_filename, session_date):
    try:
        upload_token = KalturaUploadToken()
        upload_token_result = client.uploadToken.add(upload_token)

        # Upload the file
        with open(file_path, 'rb') as file_data:
            result = client.uploadToken.upload(upload_token_result.id, file_data)

        # Create a media entry after uploading the video
        media_entry = KalturaMediaEntry()
        media_entry.name = video_title
        media_entry.mediaType = KalturaMediaType.VIDEO

        media_entry_result = client.media.add(media_entry)

        # Attach the uploaded file to the media entry
        resource = KalturaUploadedFileTokenResource()
        resource.token = upload_token_result.id

        client.media.addContent(media_entry_result.id, resource)
        logging.info(f"Video '{video_title}' uploaded to Kaltura with entry ID: {media_entry_result.id}")

        # Check if MIDAS email exists in Kaltura, otherwise use default email
        user = get_user_by_email(client, midas_email)
        admin_email = midas_email if user else DEFAULT_EMAIL

        # Update admin owner of the video
        update_kaltura_admin_owner(client, media_entry_result.id, admin_email)

        # Prepare and send email notification
        email_subject = "Your video is ready in Canvas under 'My Media'"
        email_body = f"""Dear User,

Your video titled '{video_title}' is now available in Canvas under your 'My Media' folder.

Details:
- Original Filename: {original_filename}
- Renamed Filename: {renamed_filename}
- Date: {session_date.strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
 ODU IT Services
"""
        send_email(midas_email, email_subject, email_body)

    except Exception as e:
        logging.error(f"Error uploading video to Kaltura: {str(e)}")

# Function to retrieve Monday.com board contents
def get_monday_board_contents():
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }

    query = """
    {
        boards(ids: [7202079054]) {
            id
            name
            columns {
                id
                title
                type
            }
            items_page {
                cursor
                items {
                    id 
                    name
                    column_values {
                        id
                        text
                        value
                    }
                }
            }
        }
    }
    """

    response = requests.post(url, json={'query': query}, headers=headers)
    
    if response.status_code == 200:
        try:
            data = response.json()
            return data['data']['boards'][0]  # Get the first board's data
        except KeyError as e:
            logging.error(f"Error parsing Monday.com API response: {e}")
            return None
    else:
        logging.error(f"Failed to get data from Monday.com: {response.status_code} {response.text}")
        return None

# Parse the Monday.com data to extract useful information
def cache_monday_data(board_data):
    monday_data_cache = []
    if 'items_page' in board_data:
        for item in board_data['items_page']['items']:
            
            # Filter out irrelevant items based on their names
            if item['name'] in ['Upcoming Reservations', 'Rejected Reservations', 'Past Reservations', 'Name']:
                logging.info(f"Skipping irrelevant item: {item['name']}")
                continue  # Skip irrelevant items

            session_info = {
                'course_subject': None,
                'course_number': None,
                'midas_id': None,
                'session_datetime': None,
                'email': None
            }

            for column_value in item['column_values']:
                column_id = column_value['id']
                column_text = column_value.get('text', None)  # Use 'None' as fallback if 'text' doesn't exist
                if column_id == 'course_subject__1':
                    session_info['course_subject'] = column_text
                elif column_id == 'course_number__1':
                    session_info['course_number'] = column_text
                elif column_id == 'color__1':  # Session date and start time
                    session_info['session_datetime'] = column_text
                elif column_id == 'midas_id__1':
                    session_info['midas_id'] = column_text
                elif column_id == 'email__1':
                    session_info['email'] = column_text

            date_str = session_info.get('session_datetime')
            if date_str and date_str.lower() not in ['none', 'session date and start time']:
                parsed_date = None
                for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y-%m-%d to %Y-%m-%d'):
                    try:
                        if 'to' in date_str and fmt == '%Y-%m-%d to %Y-%m-%d':
                            start_date_str = date_str.split(' to ')[0]
                            parsed_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                        else:
                            parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if parsed_date:
                    session_info['session_datetime'] = parsed_date
                    monday_data_cache.append(session_info)
                    logging.info(f"Parsed date for session: {parsed_date}")
                else:
                    logging.error(f"Error parsing date: '{date_str}' does not match expected formats.")
            else:
                logging.warning(f"Invalid or missing session_datetime for item: '{item['name']}'")

    return monday_data_cache

# Scan for new .mov files
def scan_for_new_files():
    return [f for f in os.listdir(directory_to_watch) if f.lower().endswith('.mov')]

# Match file with Monday.com data and rename it
def process_file(file, monday_data_cache):
    match = re.search(r'OBS Pro (\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})', file)
    if match:
        timestamp_str = match.group(1)
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H-%M-%S')
        except ValueError as e:
            logging.error(f"Error parsing timestamp from filename {file}: {e}")
            return

        closest_data = None
        min_diff = timedelta(minutes=60)

        for data in monday_data_cache:
            if data['session_datetime']:
                diff = abs(data['session_datetime'] - timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_data = data

        if closest_data:
            new_filename = f"{closest_data['course_number']}_{file}"
            move_and_rename_file(file, new_filename, closest_data)
        else:
            logging.info(f"No close match found for {file}")


# Move and rename the file
def move_and_rename_file(original_file, new_filename, closest_data):
    original_path = os.path.join(directory_to_watch, original_file)
    new_path = os.path.join(directory_to_recordings, new_filename)
    temp_path = os.path.join(directory_to_processing, new_filename)

    os.rename(original_path, temp_path)
    logging.info(f"File moved to processing: {temp_path}")

    os.rename(temp_path, new_path)
    logging.info(f"File moved to final recordings: {new_path}")

    # Extract additional information for email
    midas_email = closest_data['email']
    session_date = closest_data['session_datetime']
    original_filename = original_file
    renamed_filename = new_filename

    # Initialize Kaltura client and upload video
    client = init_kaltura_client()
    upload_video_to_kaltura(
        client,
        new_path,
        new_filename,
        midas_email,
        original_filename,
        renamed_filename,
        session_date
    )

#  Implementation of Send email function 
def send_email(to_address, subject, body):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from_address = os.getenv("SMTP_FROM_ADDRESS") or smtp_username  # Default 'From' address to username if not set

    if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
        logging.error("SMTP configuration is incomplete. Email not sent.")
        return

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_from_address
        msg['To'] = to_address

        with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_from_address, [to_address], msg.as_string())
        logging.info(f"Email sent to {to_address}")
    except Exception as e:
        logging.error(f"Error sending email to {to_address}: {e}")

# Main workflow
if __name__ == "__main__":
    board_structure = get_monday_board_contents()
    
    if board_structure:
        monday_data_cache = cache_monday_data(board_structure)
        new_files = scan_for_new_files()
        
        for file in new_files:
            process_file(file, monday_data_cache)
    else:
        logging.error("Failed to retrieve Monday.com board data.")


