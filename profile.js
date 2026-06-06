// Get elements
const imageInput = document.getElementById('image-upload');
const uploadButton = document.getElementById('upload-button');
const imageGallery = document.getElementById('image-gallery');
const starCountDisplay = document.getElementById('star-count-value');
const starAnimationContainer = document.getElementById('star-animation-container');
// Initialize star count
let starCount = 0;

// Add event listener to upload button
uploadButton.addEventListener('click', () => {
  // Get the selected files
  const files = imageInput.files;

  // Check if files are selected
  if (files.length > 0) {
    // Loop through files
    for (const file of files) {
      // Check if file is an image
      if (file.type.startsWith('image/')) {
        // Preview the image
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = document.createElement('img');
          img.src = e.target.result;
          imageGallery.appendChild(img);
        };
        reader.readAsDataURL(file);

        // Increment star count
        starCount++;

        // Update star count display
        starCountDisplay.textContent = starCount;

        // Create popping star animation
        const poppingStar = document.createElement('span');
        poppingStar.classList.add('popping-star');
        poppingStar.textContent = '';
        starAnimationContainer.appendChild(poppingStar);

        // Remove popping star animation after 2 seconds
        setTimeout(() => {
          poppingStar.remove();
        }, 2000);
      }
    }
  }
});