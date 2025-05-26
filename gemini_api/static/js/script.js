document.addEventListener('DOMContentLoaded', () => {
    // Tab navigation
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Text generation form
    const form = document.getElementById('generateForm');
    const submitButton = form.querySelector('.submit-btn');
    const buttonText = submitButton.querySelector('.btn-text');
    const spinner = submitButton.querySelector('.spinner');
    const responseContainer = document.getElementById('response-container');
    const aiResponse = document.getElementById('ai-response');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = errorContainer.querySelector('.error-message');

    const setLoading = (isLoading, button, text) => {
        button.disabled = isLoading;
        button.querySelector('.spinner').classList.toggle('hidden', !isLoading);
        button.querySelector('.btn-text').textContent = isLoading ? 'Processing...' : text;
    };

    const showError = (message, container) => {
        container.querySelector('.error-message').textContent = message;
        container.classList.remove('hidden');
    };

    const hideError = (container) => {
        container.classList.add('hidden');
    };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError(errorContainer);

        const formData = new FormData(form);
        const userInput = formData.get('user_input').trim();

        if (!userInput) {
            showError('Please enter some text', errorContainer);
            return;
        }

        setLoading(true, submitButton, 'Generate');

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate response');
            }

            if (data.error) {
                throw new Error(data.error);
            }

            aiResponse.textContent = data.response;
            responseContainer.classList.remove('hidden');
            form.reset();

        } catch (error) {
            showError(error.message || 'An unexpected error occurred', errorContainer);
        } finally {
            setLoading(false, submitButton, 'Generate');
        }
    });
    
    // Image analysis form
    const imageForm = document.getElementById('imageAnalyzeForm');
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('imagePreview');
    const imagePreviewContainer = document.querySelector('.image-preview-container');
    const analysisContainer = document.getElementById('analysis-container');
    const imageProcessSection = document.getElementById('image-process-section');
    const analyzedImage = document.getElementById('analyzedImage');
    const imageAnalysis = document.getElementById('image-analysis');
    const imageErrorContainer = document.getElementById('image-error-container');
    const originalImagePath = document.getElementById('originalImagePath');
    
    // Preview uploaded image
    imageInput.addEventListener('change', () => {
        const file = imageInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreviewContainer.classList.remove('hidden');
            }
            reader.readAsDataURL(file);
        } else {
            imagePreviewContainer.classList.add('hidden');
        }
    });
    
    
    // Handle image analysis form submission
    imageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError(imageErrorContainer);
        
        const formData = new FormData(imageForm);
        
        if (!imageInput.files[0]) {
            showError('Please select an image to analyze', imageErrorContainer);
            return;
        }
        
        const imageSubmitButton = imageForm.querySelector('.submit-btn');
        setLoading(true, imageSubmitButton, 'Analyze Image');
        
        try {
            const response = await fetch('/analyze-image', {
                method: 'POST',
                body: formData,
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze image');
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Display the analysis
            analyzedImage.src = data.imagePath;
            imageAnalysis.textContent = data.analysis;
            analysisContainer.classList.remove('hidden');
            imageProcessSection.classList.remove('hidden');
            
            // Set the original image path for processing
            originalImagePath.value = data.imagePath;
            
            // Reset processed image container
            document.getElementById('processed-image-container').classList.add('hidden');
            
        } catch (error) {
            showError(error.message || 'An unexpected error occurred', imageErrorContainer);
        } finally {
            setLoading(false, imageSubmitButton, 'Analyze Image');
        }
    });
    
    // Image processing form
    const processForm = document.getElementById('imageProcessForm');
    const strengthSlider = document.getElementById('strength');
    const strengthValue = document.getElementById('strengthValue');
    const processedImageContainer = document.getElementById('processed-image-container');
    const processedImage = document.getElementById('processedImage');
    const downloadLink = document.getElementById('downloadLink');
    
    // Update strength value display
    strengthSlider.addEventListener('input', () => {
        const value = Math.round(strengthSlider.value * 100);
        strengthValue.textContent = `${value}%`;
    });
    
    // Handle image processing form submission
    processForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(processForm);
        const originalImagePathValue = formData.get('originalImage');
        
        if (!originalImagePathValue) {
            showError('No image selected for processing', imageErrorContainer);
            return;
        }
        
        const processButton = processForm.querySelector('.submit-btn');
        setLoading(true, processButton, 'Apply Effect');
        
        try {
            const response = await fetch('/process-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData),
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to process image');
            }
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Display the processed image
            processedImage.src = data.processedImage;
            downloadLink.href = data.processedImage;
            processedImageContainer.classList.remove('hidden');
            
        } catch (error) {
            showError(error.message || 'An unexpected error occurred', imageErrorContainer);
        } finally {
            setLoading(false, processButton, 'Apply Effect');
        }
    });
});