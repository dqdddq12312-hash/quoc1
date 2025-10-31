import os
import sqlite3
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import threading

# Load environment variables
load_dotenv()

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), 'scheduled_posts.db')

def init_database():
    """Initialize the scheduled posts database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_type TEXT NOT NULL,
            platforms TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            media_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            posted_at TEXT,
            post_ids TEXT,
            error_message TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized")

def schedule_post(post_type, platforms, scheduled_time, content_type, content, media_path=None):
    """
    Schedule a post for future publishing

    Args:
        post_type: 'post', 'video', 'story', 'reel'
        platforms: List of platforms ['facebook', 'instagram', 'both']
        scheduled_time: datetime object or ISO format string
        content_type: 'text', 'image', 'video'
        content: Text content (message, caption, etc.)
        media_path: Path to media file (if applicable)

    Returns:
        Scheduled post ID
    """

    if isinstance(scheduled_time, datetime):
        scheduled_time_str = scheduled_time.isoformat()
    else:
        scheduled_time_str = scheduled_time

    platforms_str = json.dumps(platforms)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO scheduled_posts
        (post_type, platforms, scheduled_time, content_type, content, media_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (post_type, platforms_str, scheduled_time_str, content_type, content, media_path, 'pending'))

    post_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"✓ Post scheduled (ID: {post_id}) for {scheduled_time_str}")
    return post_id

def get_pending_posts():
    """Get all pending scheduled posts that are due"""

    current_time = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, post_type, platforms, scheduled_time, content_type, content, media_path
        FROM scheduled_posts
        WHERE status = 'pending' AND scheduled_time <= ?
        ORDER BY scheduled_time ASC
    ''', (current_time,))

    posts = cursor.fetchall()
    conn.close()

    return posts

def mark_post_as_posted(post_id, post_ids_dict):
    """Mark a scheduled post as posted"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    post_ids_json = json.dumps(post_ids_dict)
    posted_at = datetime.now().isoformat()

    cursor.execute('''
        UPDATE scheduled_posts
        SET status = 'posted', posted_at = ?, post_ids = ?
        WHERE id = ?
    ''', (posted_at, post_ids_json, post_id))

    conn.commit()
    conn.close()

def mark_post_as_failed(post_id, error_message):
    """Mark a scheduled post as failed"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE scheduled_posts
        SET status = 'failed', error_message = ?
        WHERE id = ?
    ''', (error_message, post_id))

    conn.commit()
    conn.close()

def list_scheduled_posts(status=None):
    """List all scheduled posts"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if status:
        cursor.execute('''
            SELECT id, post_type, platforms, scheduled_time, content, status
            FROM scheduled_posts
            WHERE status = ?
            ORDER BY scheduled_time DESC
        ''', (status,))
    else:
        cursor.execute('''
            SELECT id, post_type, platforms, scheduled_time, content, status
            FROM scheduled_posts
            ORDER BY scheduled_time DESC
        ''')

    posts = cursor.fetchall()
    conn.close()

    return posts

def delete_scheduled_post(post_id):
    """Delete a scheduled post"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM scheduled_posts WHERE id = ?', (post_id,))

    conn.commit()
    conn.close()

    print(f"✓ Scheduled post {post_id} deleted")

def process_scheduled_posts():
    """Process all pending scheduled posts"""

    from post_to_all import post_to_both
    from post_video import post_video_to_facebook, post_video_to_instagram, post_reel_to_instagram
    from post_story import post_photo_story_to_instagram, post_video_story_to_instagram, post_story_to_facebook

    pending_posts = get_pending_posts()

    if not pending_posts:
        print("No pending posts to process")
        return

    print(f"Processing {len(pending_posts)} scheduled post(s)...")

    for post in pending_posts:
        post_id, post_type, platforms_json, scheduled_time, content_type, content, media_path = post

        platforms = json.loads(platforms_json)

        print(f"\nProcessing post {post_id}...")
        print(f"  Type: {post_type}")
        print(f"  Platforms: {platforms}")
        print(f"  Scheduled: {scheduled_time}")

        try:
            post_ids = {}

            if post_type == 'post':
                # Regular post
                # Upload media if needed
                image_url = None
                if media_path:
                    from upload_to_s3 import upload_file_to_s3
                    if os.path.exists(media_path):
                        image_url = upload_file_to_s3(media_path)
                    else:
                        image_url = media_path

                if 'facebook' in platforms or 'both' in platforms:
                    from post_to_facebook import post_to_facebook
                    fb_id = post_to_facebook(content, image_url)
                    post_ids['facebook'] = fb_id

                if 'instagram' in platforms or 'both' in platforms:
                    if image_url:
                        from post_to_instagram import post_image_to_instagram
                        ig_id = post_image_to_instagram(image_url, content)
                        post_ids['instagram'] = ig_id

            elif post_type == 'video':
                if 'facebook' in platforms or 'both' in platforms:
                    fb_id = post_video_to_facebook(media_path, content, content)
                    post_ids['facebook'] = fb_id

                if 'instagram' in platforms or 'both' in platforms:
                    ig_id = post_video_to_instagram(media_path, content)
                    post_ids['instagram'] = ig_id

            elif post_type == 'reel':
                if 'instagram' in platforms or 'both' in platforms:
                    ig_id = post_reel_to_instagram(media_path, content)
                    post_ids['instagram'] = ig_id

            elif post_type == 'story':
                if 'facebook' in platforms or 'both' in platforms:
                    fb_id = post_story_to_facebook(media_path)
                    post_ids['facebook'] = fb_id

                if 'instagram' in platforms or 'both' in platforms:
                    if content_type == 'video':
                        ig_id = post_video_story_to_instagram(media_path)
                    else:
                        ig_id = post_photo_story_to_instagram(media_path)
                    post_ids['instagram'] = ig_id

            mark_post_as_posted(post_id, post_ids)
            print(f"✓ Post {post_id} published successfully")

        except Exception as e:
            error_msg = str(e)
            mark_post_as_failed(post_id, error_msg)
            print(f"✗ Post {post_id} failed: {error_msg}")

def run_scheduler_daemon(check_interval=60):
    """
    Run the scheduler as a background daemon

    Args:
        check_interval: Seconds between checks (default: 60)
    """

    print(f"Scheduler daemon started (checking every {check_interval} seconds)")
    print("Press Ctrl+C to stop")

    try:
        while True:
            process_scheduled_posts()
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("\nScheduler stopped")

if __name__ == "__main__":
    # Initialize database
    init_database()

    # Example: Schedule a post
    # from datetime import datetime, timedelta

    # Schedule a post for 5 minutes from now
    # scheduled_time = datetime.now() + timedelta(minutes=5)
    # schedule_post(
    #     post_type='post',
    #     platforms=['facebook', 'instagram'],
    #     scheduled_time=scheduled_time,
    #     content_type='image',
    #     content='Scheduled post test!',
    #     media_path='path/to/image.jpg'
    # )

    # List scheduled posts
    print("\nScheduled Posts:")
    print("=" * 60)
    posts = list_scheduled_posts()
    for post in posts:
        print(f"ID: {post[0]}, Type: {post[1]}, Platforms: {post[2]}")
        print(f"  Scheduled: {post[3]}, Status: {post[5]}")
        print(f"  Content: {post[4][:50]}...")
        print()

    # To run the scheduler daemon:
    # run_scheduler_daemon(check_interval=60)