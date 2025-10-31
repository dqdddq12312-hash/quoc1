import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment
PAGE_ID = os.getenv('FB_PAGE_ID')
PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')

def post_to_facebook(message, media_path=None):
    try:
        if media_path:
            # Determine if it's a video or image based on file extension
            is_video = media_path.lower().endswith(('.mp4', '.mov', '.avi'))
            
            if is_video:
                url = f"https://graph.facebook.com/v24.0/{PAGE_ID}/videos"
            else:
                url = f"https://graph.facebook.com/v24.0/{PAGE_ID}/photos"
            
            # Prepare the files and data for multipart upload
            files = {
                'source': open(media_path, 'rb')
            }
            payload = {
                'message': message,
                'access_token': PAGE_ACCESS_TOKEN
            }
            
            response = requests.post(url, files=files, data=payload)
        else:
            # Text-only posts
            url = f"https://graph.facebook.com/v24.0/{PAGE_ID}/feed"
            payload = {
                'message': message,
                'access_token': PAGE_ACCESS_TOKEN
            }
            response = requests.post(url, data=payload)

        response.raise_for_status()
        result = response.json()
        post_id = result.get('post_id') or result.get('id')
        print(f"Success! Post ID: {post_id}")
        return post_id

    except requests.exceptions.RequestException as e:
        print(f"Error posting to Facebook: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None
    finally:
        # Close the file if it was opened
        if media_path and 'files' in locals():
            files['source'].close()

if __name__ == "__main__":
    # Test message
    message = "Hello! This is a test post from my Facebook automation tool."

    print(f"Posting to page: {PAGE_ID}")
    post_to_facebook(message)