from flask import Flask, render_template, request, redirect, url_for, flash
import fb_posting
import os
from werkzeug.utils import secure_filename

# Get the absolute path of the current directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

# Create the Flask app with explicit template folder
app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = 'your_secret_key'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        message = request.form.get('message')
        media = request.files.get('media')
        media_path = None
        if media and media.filename:
            filename = secure_filename(media.filename)
            media_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media.save(media_path)
        try:
            post_id = fb_posting.post_to_facebook(message, media_path)
            if post_id:
                flash(f'Success! Post ID: {post_id}', 'success')
            else:
                flash('Failed to post to Facebook.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        finally:
            if media_path and os.path.exists(media_path):
                os.remove(media_path)
        return redirect(url_for('index'))
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
