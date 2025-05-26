import pytest
import os
import json
from app import app
from io import BytesIO

@pytest.fixture
def client():
    # Configure app for testing
    app.config["TESTING"] = True
    # Create test upload directories
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/processed', exist_ok=True)
    with app.test_client() as client:
        yield client

def test_home_page_with_image_tab(client):
    """Test that home page contains image analysis tab"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"AI Image Analyzer" in response.data
    assert b"Image Analysis" in response.data

def test_analyze_image_endpoint(client):
    """Test the /analyze-image endpoint with a test image"""
    # Create a simple test image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    
    # Send the test image to the endpoint
    data = {
        'image': (img_io, 'test_image.jpg')
    }
    
    response = client.post('/analyze-image', 
                           content_type='multipart/form-data',
                           data=data)
    
    # This may fail if API key is not set or API is not available
    # In a real test environment, you would mock the API call
    if response.status_code == 200:
        data = response.get_json()
        assert 'analysis' in data
        assert 'imagePath' in data
        assert data['imagePath'].startswith('/static/uploads/')
    else:
        # If API is not available, just check for proper error handling
        data = response.get_json()
        assert 'error' in data

def test_process_image_endpoint(client):
    """Test the /process-image endpoint with a test image"""
    # First create and save a test image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'blue')
    test_path = os.path.join('static/uploads', 'test_process.jpg')
    img.save(test_path)
    
    # Now process the image
    data = {
        'originalImage': '/static/uploads/test_process.jpg',
        'operation': 'blur',
        'strength': '0.5'
    }
    
    response = client.post('/process-image',
                          data=data)
    
    # Check response
    assert response.status_code == 200
    result = response.get_json()
    assert 'processedImage' in result
    assert result['processedImage'].startswith('/static/processed/')
    
    # Clean up test files
    if os.path.exists(test_path):
        os.remove(test_path)
    
    processed_path = result['processedImage'].replace('/static/', '')
    processed_path = os.path.join('static', processed_path)
    if os.path.exists(processed_path):
        os.remove(processed_path)