from flask import Flask, request, jsonify, render_template, url_for
import requests
from dotenv import load_dotenv
import os
import base64
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import json
from PIL import Image, ImageFilter, ImageEnhance
import io
import uuid
import time # Add time module
import datetime # Add datetime module
import threading # Add threading module

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    raise ValueError("API_KEY must be set in .env file")

# Flask app setup
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
app.config['PROCESSED_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/processed')
# Add cleanup configuration
app.config['DAYS_TO_KEEP_FILES'] = 7  # Number of days to keep files
app.config['CLEANUP_INTERVAL_SECONDS'] = 24 * 60 * 60  # Cleanup every 24 hours

# Create upload folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# API configuration
BASE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TEXT_MODEL = "gemini-1.5-flash-001"  # Updated text model
VISION_MODEL = "gemini-1.5-pro-001"  # Updated vision model

class APIError(Exception):
    """Custom exception for API related errors"""
    pass

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_input(text):
    """Validate user input"""
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")
    if len(text) > 1000:  # Adjust limit as needed
        raise ValueError("Input text is too long (max 1000 characters)")
    return text.strip()

def process_api_response(response_data):
    """Process and validate API response"""
    try:
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise APIError("No candidates found in API response")
        first_candidate = candidates[0]
        parts = first_candidate.get("content", {}).get("parts", [])
        if not parts:
            raise APIError("No parts found in the first candidate")
        return parts[0].get("text", "")
    except (KeyError, IndexError):
        raise APIError("Unable to extract response text from API")

def encode_image(image_path):
    """Encode image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image(original_path, operation, strength=0.5):
    """Apply various transformations to make the image harder to identify"""
    img = Image.open(original_path)
    
    # Create a unique filename for the processed image
    filename = f"processed_{uuid.uuid4().hex}.jpg"
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    
    # Apply the selected operation
    if operation == "blur":
        # Apply Gaussian blur
        img = img.filter(ImageFilter.GaussianBlur(radius=float(strength) * 5))
    elif operation == "pixelate":
        # Pixelate by resizing down and up
        small_size = max(1, int((1 - float(strength)) * min(img.size)))
        img = img.resize((small_size, small_size), Image.NEAREST)
        img = img.resize(img.size, Image.NEAREST)
    elif operation == "contrast":
        # Adjust contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.0 + float(strength) * 2)
    elif operation == "brighten":
        # Adjust brightness
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0 + float(strength))
    elif operation == "darken":
        # Darken the image
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0 - float(strength) * 0.7)
    elif operation == "noise":
        # Simple noise effect (this is a basic implementation)
        from random import randint
        noise_img = img.copy()
        pixels = noise_img.load()
        noise_level = int(float(strength) * 50)
        
        for i in range(noise_img.width):
            for j in range(noise_img.height):
                if randint(0, 100) < noise_level:
                    pixels[i, j] = (randint(0, 255), randint(0, 255), randint(0, 255))
        img = noise_img
    
    # Save the processed image
    img = img.convert('RGB')  # Convert to RGB to ensure compatibility
    img.save(output_path, "JPEG", quality=95)
    
    return filename

def cleanup_old_files(folder_path, days_threshold):
    """Deletes files older than the specified number of days from the folder."""
    app.logger.info(f"Running cleanup for folder: {folder_path}")
    now = datetime.datetime.now()
    threshold_date = now - datetime.timedelta(days=days_threshold)
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                file_modified_time_timestamp = os.path.getmtime(file_path)
                file_modified_time = datetime.datetime.fromtimestamp(file_modified_time_timestamp)
                
                if file_modified_time < threshold_date:
                    os.remove(file_path)
                    app.logger.info(f"Deleted old file: {file_path}")
        except Exception as e:
            app.logger.error(f"Error deleting file {file_path}: {e}")

def run_cleanup_scheduler():
    """Periodically runs the cleanup function for uploads and processed folders."""
    while True:
        days_to_keep = app.config['DAYS_TO_KEEP_FILES']
        cleanup_old_files(app.config['UPLOAD_FOLDER'], days_to_keep)
        cleanup_old_files(app.config['PROCESSED_FOLDER'], days_to_keep)
        time.sleep(app.config['CLEANUP_INTERVAL_SECONDS'])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        # Validate input
        user_input = validate_input(request.form.get("user_input", ""))

        # Prepare request data
        data = {
            "contents": [
                {
                    "parts": [{"text": user_input}]
                }
            ]
        }

        # Send request to API
        response = requests.post(
            f"{BASE_API_URL}/{TEXT_MODEL}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=30  # Add timeout
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Process response
        result = response.json()
        ai_response = process_api_response(result)
        
        return jsonify({"response": ai_response})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except requests.exceptions.Timeout:
        app.logger.error("Request timed out") # Log detailed error
        return jsonify({"error": "Request timed out"}), 504
    except requests.exceptions.RequestException as e:
        # Log the full error for server-side debugging, but don't expose it to the client
        app.logger.error(f"Failed to communicate with API: {str(e)}")
        return jsonify({"error": "Failed to communicate with API. Please check server logs for details."}), 502
    except APIError as e:
        app.logger.error(f"API Error: {str(e)}") # Log detailed error
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500





@app.route("/analyze-image", methods=["POST"])
def analyze_image():
    try:
        # ... (既存のファイルチェック処理など) ...

        # Encode image to base64
        image_data = encode_image(filepath)
        
        # Prepare request data with image
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Analyze this image in detail. What can you identify in this image? Explain your reasoning process step by step. Then, explain what specific visual elements would make this image harder to identify if they were altered."
                        },
                        {
                            "inline_data": {
                                "mime_type": f"image/{filepath.split('.')[-1].lower()}",
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
        }
        
        api_url = f"{BASE_API_URL}/{VISION_MODEL}:generateContent?key={api_key}"
        app.logger.info(f"Sending request to Vision API: {api_url}")
        # app.logger.debug(f"Request data: {json.dumps(data)}") # 画像データが大きいため、必要に応じてコメントアウトを解除

        # Send request to Vision API
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=30  # タイムアウトを30秒に設定
        )
        
        app.logger.info(f"Vision API response status code: {response.status_code}")
        app.logger.info(f"Vision API response text: {response.text}") # APIからの生のレスポンスを出力

        # Check for HTTP errors
        response.raise_for_status()
        
        # Process response
        result = response.json()
        analysis = process_api_response(result) #
        
        return jsonify({
            "analysis": analysis,
            "imagePath": url_for('static', filename=f'uploads/{unique_filename}')
        })
        
    # ... (既存の例外処理) ...
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to communicate with Vision API: {str(e)}")
        # APIからのレスポンスオブジェクト `response` が存在すれば、それもログに出力するとさらに詳細がわかる場合があります。
        # ただし、RequestExceptionの段階ではresponseオブジェクトが存在しないことも多いです。
        # if 'response' in locals() and response is not None:
        #    app.logger.error(f"Underlying API Response (if any): {response.text}")
        return jsonify({"error": "Failed to communicate with Vision API. Please check server logs for details."}), 502
    # ... (その他の例外処理) ...




@app.route("/process-image", methods=["POST"])
def process_image_endpoint():
    try:
        # Get the form data
        original_image_path = request.form.get("originalImage", "")
        operation = request.form.get("operation", "blur")
        strength = request.form.get("strength", "0.5")
        
        # Validate inputs
        if not original_image_path:
            return jsonify({"error": "No original image path provided"}), 400
            
        # Convert URL path to filesystem path
        if original_image_path.startswith('/static/uploads/'):
            original_image_path = original_image_path.replace('/static/uploads/', '')
            original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], original_image_path)
        else:
            return jsonify({"error": "Invalid image path"}), 400
            
        # Process the image
        processed_filename = process_image(original_image_path, operation, strength)
        processed_image_url = url_for('static', filename=f'processed/{processed_filename}')
        
        # Return the processed image URL
        return jsonify({
            "processedImage": processed_image_url,
            "message": f"Image processed with {operation} effect"
        })
        
    except Exception as e:
        app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500

if __name__ == "__main__":
    # Start the cleanup scheduler in a background thread
    cleanup_thread = threading.Thread(target=run_cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    app.run(debug=True)