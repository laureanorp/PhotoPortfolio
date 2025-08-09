import logging
import os
import subprocess
from typing import List
from PIL import Image
from bs4 import BeautifulSoup
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

input_folder = "/Users/laureanoruiz/Desktop/MY STUFF/CODING/PhotoPortfolio/new_photos"
output_folder = "/Users/laureanoruiz/Desktop/MY STUFF/CODING/PhotoPortfolio/photos_resized"
html_file = "index.html"

MAX_WIDTH = 1500
MAX_HEIGHT = 2000


def normalize_filename(filename: str) -> str:
    """
    Normalize unicode filename to NFC form to avoid issues with special characters like ñ.
    """
    return unicodedata.normalize('NFC', filename)


def resize_image(input_path: str, output_path: str) -> bool:
    """
    Resize an image preserving aspect ratio to fit within MAX_WIDTH and MAX_HEIGHT.
    Save the resized image to output_path.
    Returns True if successful, False otherwise.
    """
    try:
        with Image.open(input_path) as img:
            original_size = img.size
            width, height = original_size

            scale_w = MAX_WIDTH / width if width > MAX_WIDTH else 1
            scale_h = MAX_HEIGHT / height if height > MAX_HEIGHT else 1
            scale = min(scale_w, scale_h)

            if scale < 1:
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            else:
                new_size = original_size

            img.save(output_path)
            logging.info(f"Resized '{input_path}' from {original_size} to {new_size}")
            return True
    except Exception as e:
        logging.error(f"Error resizing image {input_path}: {e}")
        return False


def get_next_index(output_folder: str) -> int:
    """
    Scan the output folder and find the next available numeric index
    based on the existing files with prefix numbers.
    """
    valid_exts = ('.jpg', '.jpeg', '.png')
    files = os.listdir(output_folder)
    indices = []
    for f in files:
        if f.startswith('.'):  # ignore hidden files
            continue
        if not f.lower().endswith(valid_exts):  # ignore non-image files
            continue
        if '_' not in f:
            raise ValueError(f"File '{f}' in output folder does not have an index prefix.")
        prefix = f.split('_')[0]
        if not prefix.isdigit():
            raise ValueError(f"File '{f}' in output folder has invalid index prefix.")
        indices.append(int(prefix))
    return max(indices) + 1 if indices else 1


def process_images(input_folder: str, output_folder: str) -> List[str]:
    """
    Process all images from input_folder:
    resize them, save to output_folder with numeric prefix,
    delete original, and return list of new filenames.
    """
    logging.info("Processing and resizing images...")
    input_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not input_files:
        logging.info("No images found in input folder.")
        return []

    try:
        start_index = get_next_index(output_folder)
    except ValueError as e:
        logging.error(f"Error: {e}")
        return []

    new_files = []
    idx = start_index

    for fname in input_files:
        input_path = os.path.join(input_folder, fname)
        normalized_name = normalize_filename(fname)
        output_fname = f"{idx}_{normalized_name}"
        output_path = os.path.join(output_folder, output_fname)

        success = resize_image(input_path, output_path)
        if success:
            try:
                os.remove(input_path)
            except Exception as e:
                logging.warning(f"Could not delete original image '{input_path}': {e}")
            new_files.append(output_fname)
            idx += 1

    return new_files


def update_html_only_photogrid(html_file: str, output_folder: str, new_images: List[str]) -> None:
    """
    Update the photo-grid div in the given HTML file by adding new_images
    at the top and reordering all images descending by their numeric prefix.
    """
    logging.info("Updating HTML photo grid...")
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    photo_grid = soup.find('div', class_='photo-grid')
    if photo_grid is None or not hasattr(photo_grid, 'find_all'):
        logging.error("Error: 'photo-grid' div not found in HTML or is not a valid tag.")
        return

    from bs4.element import Tag
    current_imgs = {os.path.basename(str(img.get('src', ''))) for img in photo_grid.find_all('img') if isinstance(img, Tag) and img.get('src')}

    new_images = [img for img in new_images if img not in current_imgs]
    if not new_images:
        logging.info("No new images to add to HTML.")
        return

    new_images_sorted = sorted(new_images, key=lambda f: int(f.split('_')[0]))

    # Insert new images at the beginning
    for fname in reversed(new_images_sorted):
        img_tag = soup.new_tag("img", src=f"photos_resized/{fname}", alt=fname.rsplit('.', 1)[0], loading="lazy")
        if hasattr(photo_grid, "insert"):
            photo_grid.insert(0, img_tag)
            photo_grid.insert(1, soup.new_string("\n  "))

    # Reorder all imgs descending by index
    all_imgs = photo_grid.find_all('img')
    def img_index(img) -> int:
        try:
            return int(os.path.basename(img['src']).split('_')[0])
        except Exception:
            return -1
    sorted_imgs = sorted(all_imgs, key=img_index, reverse=True)

    photo_grid.clear()
    for img in sorted_imgs:
        photo_grid.append(img)
        photo_grid.append(soup.new_string("\n  "))

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())

    logging.info(f"🌟 HTML updated successfully: added {len(new_images)} new image(s).")


def git_commit_and_push(num_new_images: int, commit_message: str = None) -> None:
    """
    Adds all changes, commits with the given message, and pushes to the current branch,
    but asks for user confirmation before pushing.
    """
    if commit_message is None:
        commit_message = f"Add {num_new_images} new photos (automatically updated HTML)"

    logging.info(f"📦 Ready to push {num_new_images} new photo(s) to portfolio repo.")

    while True:
        confirm = input(f"Do you want to commit and push these changes? (Y/N): ").strip().lower()
        if confirm in ('y', 'n'):
            break
        print("Please enter 'Y' or 'N'.")

    if confirm != 'y':
        logging.info("Push cancelled by user.")
        return

    try:
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            logging.info("No changes detected in git. Nothing to commit or push.")
            return

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "push", "origin", branch], check=True)

        logging.info("✅ Git push successful.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during git operations: {e}")


def main() -> None:
    logging.info("Script started!")
    new_images = process_images(input_folder, output_folder)
    if new_images:
        update_html_only_photogrid(html_file, output_folder, new_images)
        logging.info("\n📂 Process Complete!")
        logging.info(f"✅ {len(new_images)} new image(s) resized and saved to '{output_folder}'.")
        logging.info(f"🖼️ {len(new_images)} new image(s) added to the HTML file '{html_file}'.")
        git_commit_and_push(len(new_images))
    else:
        logging.info("No images processed.")


if __name__ == "__main__":
    main()
