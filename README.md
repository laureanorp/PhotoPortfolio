# Photo Portfolio Upload Script

I wanted a plain and simple web for uploading my photos, publishing it via GitHub pages. Pure HTML/CSS, no JS, no libraries.

Since I didn't want to manually add new images to my HTML, I coded a (dirty but functional) script that compresses and uploads new images to the portfolio, also pushing the changes to GitHub. 
Images to be added to the portfolio are placed on an input folder. When the script runs, they are compressed to a configurable max size, an index (number) is added to the name, and they are moved to the output folder. The necessary HTML img tags are added to the HTML and the changes are pushed to your repo.

To check your portfolio, you must configure Github Pages in your repo settings.

## Setup & Usage

1. Clone the repository and update the `input_folder` and `output_folder` paths in `upload_images_script.py` to match your local setup.

2. Create a virtual environment and install dependencies with `pip install -r requirements.txt`

3. Clear the existing images inside the `<div class="photo-grid">` in your index.html file, since those are my photos :)

4. Add the new images files you want to upload into your desired input folder

5. Run the script: `python upload_images_script.py`.

6. A summary will appear on the console. Confirm that you want to push your changes.
