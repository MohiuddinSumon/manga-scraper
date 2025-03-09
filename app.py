import glob
import os
import re
import time
import urllib.parse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image

# Set page config
st.set_page_config(page_title="Manga Downloader", page_icon="📚", layout="wide")


def get_manga_title(soup, url):
    """Extract manga title from the main page or fallback to domain name"""
    # Try to get title from common selectors
    title_selectors = ["h1", ".manga-title", ".series-title", "title"]

    for selector in title_selectors:
        title_element = soup.select_one(selector)
        if title_element and title_element.text.strip():
            # Clean title by removing terms like "manga", "read online", etc.
            title = title_element.text.strip()
            title = re.sub(
                r"\s*-?\s*(manga|read online|free|scans).*$",
                "",
                title,
                flags=re.IGNORECASE,
            )
            return title.strip()

    # Fallback to domain name
    domain = urllib.parse.urlparse(url).netloc
    domain = domain.replace("www.", "").split(".")[0]
    return domain.title()


def fetch_chapter_links(url, chapter_regex):
    """Fetch all chapter links from the main page"""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        manga_title = get_manga_title(soup, url)

        # Find all links
        all_links = soup.find_all("a", href=True)

        # Compile regex pattern
        pattern = re.compile(chapter_regex)

        # Extract chapter links and numbers
        chapters = {}
        for link in all_links:
            href = link["href"]
            match = pattern.search(href)

            if match:
                chapter_num = match.group(1)
                full_url = urllib.parse.urljoin(url, href)
                chapters[chapter_num] = full_url

        # Sort chapters by number (numeric sort)
        sorted_chapters = {
            k: chapters[k] for k in sorted(chapters.keys(), key=lambda x: int(x))
        }

        return manga_title, sorted_chapters

    except requests.RequestException as e:
        st.error(f"Error fetching page: {e}")
        return None, {}
    except Exception as e:
        st.error(f"Error processing page: {e}")
        return None, {}


def is_chapter_downloaded(manga_title, chapter_num, min_images=3):
    """Check if chapter is already downloaded with at least min_images"""
    chapter_dir = os.path.join("comics", manga_title, f"Chapter {chapter_num}")

    if not os.path.exists(chapter_dir):
        return False

    # Check if directory contains minimum number of images
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    image_count = 0

    for ext in image_extensions:
        image_count += len(glob.glob(os.path.join(chapter_dir, f"*{ext}")))

    return image_count >= min_images


def download_chapter_images(
    chapter_url,
    manga_title,
    chapter_num,
    container_selector=None,
    delay=1.0,
    skip_existing=True,
):
    """Download all images from a chapter page"""
    # Check if already downloaded
    if skip_existing and is_chapter_downloaded(manga_title, chapter_num):
        st.info(f"Skipping Chapter {chapter_num} (already downloaded)")
        return 0, True  # Return 0 downloaded, but was skipped

    try:
        response = requests.get(chapter_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # If a container selector is provided, narrow down the search
        if container_selector and container_selector.strip():
            try:
                container = soup.select_one(container_selector)
                if container:
                    img_elements = container.find_all("img")
                else:
                    img_elements = soup.find_all("img")
            except Exception:
                img_elements = soup.find_all("img")
        else:
            # Look for images within paragraph tags first
            p_tags = soup.find_all("p")
            img_elements = []

            for p in p_tags:
                img_elements.extend(p.find_all("img"))

            # If no images found in p tags, get all img tags
            if not img_elements:
                img_elements = soup.find_all("img")

        # Create directory
        chapter_dir = os.path.join("comics", manga_title, f"Chapter {chapter_num}")
        os.makedirs(chapter_dir, exist_ok=True)

        # Download images
        image_count = len(img_elements)
        downloaded = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, img in enumerate(img_elements):
            # Get image URL (try src, data-src, and data-lazy-src attributes)
            img_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")

            if img_url:
                # Skip small icons, advertisements, etc.
                if (
                    "icon" in img_url.lower()
                    or "logo" in img_url.lower()
                    or "ad" in img_url.lower()
                ):
                    continue

                # Ensure absolute URL
                img_url = urllib.parse.urljoin(chapter_url, img_url)

                try:
                    # Add delay to avoid overwhelming the server
                    time.sleep(delay)

                    img_response = requests.get(
                        img_url, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    img_response.raise_for_status()

                    # Save image with zero-padded index
                    file_ext = (
                        os.path.splitext(urllib.parse.urlparse(img_url).path)[1]
                        or ".jpg"
                    )
                    if not file_ext.startswith("."):
                        file_ext = "." + file_ext

                    img_filename = os.path.join(
                        chapter_dir, f"image_{i+1:02d}{file_ext}"
                    )

                    with open(img_filename, "wb") as f:
                        f.write(img_response.content)

                    downloaded += 1
                    progress_bar.progress(
                        downloaded / image_count if image_count > 0 else 1.0
                    )
                    status_text.text(
                        f"Downloading Chapter {chapter_num}: {downloaded}/{image_count} images"
                    )

                except Exception as e:
                    st.warning(
                        f"Error downloading image {i+1} from chapter {chapter_num}: {e}"
                    )

        return downloaded, False  # Return downloaded count and not skipped

    except Exception as e:
        st.error(f"Error processing chapter {chapter_num}: {e}")
        return 0, False  # Return 0 downloaded and not skipped


def get_available_manga():
    """Get list of downloaded manga folders"""
    if not os.path.exists("comics"):
        return []

    return [
        name
        for name in os.listdir("comics")
        if os.path.isdir(os.path.join("comics", name))
    ]


def get_available_chapters(manga_title):
    """Get list of downloaded chapter folders for a manga"""
    manga_dir = os.path.join("comics", manga_title)
    if not os.path.exists(manga_dir):
        return []

    chapter_dirs = [
        name
        for name in os.listdir(manga_dir)
        if os.path.isdir(os.path.join(manga_dir, name)) and name.startswith("Chapter ")
    ]

    # Sort numerically
    chapter_dirs.sort(key=lambda x: int(x.split("Chapter ")[1]))
    return chapter_dirs


def get_chapter_images(manga_title, chapter):
    """Get list of image files in a chapter folder"""
    chapter_dir = os.path.join("comics", manga_title, chapter)

    if not os.path.exists(chapter_dir):
        return []

    # Get all image files
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    images = []

    for ext in image_extensions:
        images.extend(glob.glob(os.path.join(chapter_dir, f"*{ext}")))

    # Sort by filename (should be image_01, image_02, etc.)
    images.sort()
    return images


# Main UI
st.title("Manga Chapter & Image Downloader")
tab1, tab2 = st.tabs(["Download", "Browse"])

with tab1:
    st.subheader("Download Manga Chapters")

    url = st.text_input("Main Page URL", placeholder="https://example.com/manga/title")
    regex = st.text_input(
        "Chapter Number Regex",
        value=r"chapter-(\d+)",
        help="Regular expression to extract chapter numbers from URLs",
    )

    col1, col2 = st.columns(2)

    with col1:
        container_selector = st.text_input(
            "Container Selector (Optional)",
            placeholder=".chapter-content",
            help="CSS selector for the container with chapter images",
        )

    with col2:
        delay = st.slider(
            "Request Delay (seconds)",
            0.5,
            5.0,
            1.0,
            0.5,
            help="Delay between requests to avoid server overload",
        )

    skip_existing = st.checkbox(
        "Skip Already Downloaded Chapters",
        value=True,
        help="Skip chapters that have already been downloaded",
    )

    if st.button("Fetch Chapters"):
        if not url or not regex:
            st.error("Please enter both URL and chapter regex pattern")
        else:
            with st.spinner("Fetching chapters..."):
                try:
                    manga_title, chapters = fetch_chapter_links(url, regex)

                    if manga_title and chapters:
                        st.session_state.manga_title = manga_title
                        st.session_state.chapters = chapters
                        st.session_state.container_selector = container_selector
                        st.session_state.delay = delay
                        st.session_state.skip_existing = skip_existing

                        st.success(
                            f"Found {len(chapters)} chapters for '{manga_title}'"
                        )
                    else:
                        st.error(
                            "No chapters found. Please check the URL and regex pattern."
                        )

                except Exception as e:
                    st.error(f"Error: {e}")

    if "chapters" in st.session_state and st.session_state.chapters:
        with st.expander("Available Chapters", expanded=True):
            manga_title = st.session_state.manga_title

            st.write(f"Manga: **{manga_title}**")
            st.write(f"Total Chapters: **{len(st.session_state.chapters)}**")

            col1, col2 = st.columns(2)

            with col1:
                # Display chapter selection options
                chapters_to_download = st.multiselect(
                    "Select chapters to download",
                    options=sorted(
                        st.session_state.chapters.keys(), key=lambda x: int(x)
                    ),
                    help="Hold Ctrl/Cmd to select multiple chapters",
                )

                if st.button("Download Selected Chapters"):
                    if not chapters_to_download:
                        st.warning("Please select at least one chapter")
                    else:
                        total_chapters = len(chapters_to_download)
                        total_images = 0
                        skipped_chapters = 0

                        chapter_progress = st.progress(0)
                        overall_status = st.empty()

                        for i, chapter_num in enumerate(chapters_to_download):
                            chapter_url = st.session_state.chapters[chapter_num]
                            overall_status.text(
                                f"Processing chapter {chapter_num} ({i+1}/{total_chapters})"
                            )

                            images_count, was_skipped = download_chapter_images(
                                chapter_url,
                                manga_title,
                                chapter_num,
                                st.session_state.container_selector,
                                st.session_state.delay,
                                st.session_state.skip_existing,
                            )

                            if was_skipped:
                                skipped_chapters += 1

                            total_images += images_count
                            chapter_progress.progress((i + 1) / total_chapters)

                        if skipped_chapters > 0:
                            overall_status.text(
                                f"Download complete! {total_images} images downloaded across {total_chapters - skipped_chapters} chapters. {skipped_chapters} chapters were skipped."
                            )
                        else:
                            overall_status.text(
                                f"Download complete! {total_images} images downloaded across {total_chapters} chapters."
                            )

                        st.success(
                            f"Successfully downloaded {total_chapters - skipped_chapters} chapters of '{manga_title}'"
                        )

            with col2:
                # Add a "Download All" button
                if st.button("Download All Chapters"):
                    chapter_nums = sorted(
                        st.session_state.chapters.keys(), key=lambda x: int(x)
                    )
                    total_chapters = len(chapter_nums)
                    total_images = 0
                    skipped_chapters = 0

                    chapter_progress = st.progress(0)
                    overall_status = st.empty()

                    for i, chapter_num in enumerate(chapter_nums):
                        chapter_url = st.session_state.chapters[chapter_num]
                        overall_status.text(
                            f"Processing chapter {chapter_num} ({i+1}/{total_chapters})"
                        )

                        images_count, was_skipped = download_chapter_images(
                            chapter_url,
                            manga_title,
                            chapter_num,
                            st.session_state.container_selector,
                            st.session_state.delay,
                            st.session_state.skip_existing,
                        )

                        if was_skipped:
                            skipped_chapters += 1

                        total_images += images_count
                        chapter_progress.progress((i + 1) / total_chapters)

                    if skipped_chapters > 0:
                        overall_status.text(
                            f"Download complete! {total_images} images downloaded across {total_chapters - skipped_chapters} chapters. {skipped_chapters} chapters were skipped."
                        )
                    else:
                        overall_status.text(
                            f"Download complete! {total_images} images downloaded across {total_chapters} chapters."
                        )

                    st.success(
                        f"Successfully downloaded {total_chapters - skipped_chapters} chapters of '{manga_title}'"
                    )

with tab2:
    st.subheader("Browse Downloaded Manga")

    available_manga = get_available_manga()

    if not available_manga:
        st.info("No manga downloaded yet. Use the Download tab to get started!")
    else:
        selected_manga = st.selectbox("Select Manga", available_manga)

        if selected_manga:
            available_chapters = get_available_chapters(selected_manga)

            if not available_chapters:
                st.info(f"No chapters found for {selected_manga}")
            else:
                selected_chapter = st.selectbox("Select Chapter", available_chapters)

                if selected_chapter:
                    chapter_images = get_chapter_images(
                        selected_manga, selected_chapter
                    )

                    if not chapter_images:
                        st.info(f"No images found in {selected_chapter}")
                    else:
                        # Initialize session state for image viewing
                        if "image_index" not in st.session_state:
                            st.session_state.image_index = 0

                        # Ensure the index is within bounds
                        if st.session_state.image_index >= len(chapter_images):
                            st.session_state.image_index = 0

                        # Display current image number and navigation controls
                        col1, col2, col3 = st.columns([1, 3, 1])
                        with col1:
                            if st.button("⬅️ Previous"):
                                st.session_state.image_index = max(
                                    0, st.session_state.image_index - 1
                                )
                                st.rerun()

                        with col2:
                            st.write(
                                f"**Image {st.session_state.image_index + 1}/{len(chapter_images)}**"
                            )

                        with col3:
                            if st.button("Next ➡️"):
                                st.session_state.image_index = min(
                                    len(chapter_images) - 1,
                                    st.session_state.image_index + 1,
                                )
                                st.rerun()

                        # Display the current image using Streamlit's native image component
                        try:
                            image_path = chapter_images[st.session_state.image_index]
                            image = Image.open(image_path)

                            # Create container for image with adjustable width
                            img_container = st.container()

                            # Add zoom control
                            zoom_factor = st.slider(
                                "Zoom", min_value=50, max_value=200, value=100, step=10
                            )

                            # Calculate new dimensions based on zoom
                            orig_width, orig_height = image.size
                            new_width = int(orig_width * zoom_factor / 100)

                            # Display image with zoom applied
                            with img_container:
                                st.image(
                                    image, width=new_width, use_container_width=False
                                )

                            # Add keyboard shortcut info
                            with st.expander("Keyboard Navigation"):
                                st.write(
                                    """
                                Use the buttons to navigate between images.
                                Adjust the zoom slider to resize the image.
                                
                                Tip: You can also use keyboard shortcuts:
                                - 'n' for next image
                                - 'p' for previous image
                                - Use the Home key to return to the first image
                                """
                                )

                                # Check for keyboard input (limited functionality but gives some options)
                                key_pressed = st.text_input(
                                    "Press 'n' for next, 'p' for previous, 'h' for first image",
                                    "",
                                    key="key_input",
                                )
                                if key_pressed.lower() == "n":
                                    st.session_state.image_index = min(
                                        len(chapter_images) - 1,
                                        st.session_state.image_index + 1,
                                    )
                                    st.rerun()
                                elif key_pressed.lower() == "p":
                                    st.session_state.image_index = max(
                                        0, st.session_state.image_index - 1
                                    )
                                    st.rerun()
                                elif key_pressed.lower() == "h":
                                    st.session_state.image_index = 0
                                    st.rerun()

                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                            st.info("Try selecting a different chapter or manga.")
