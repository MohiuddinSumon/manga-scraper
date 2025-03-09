import base64
import glob
import hashlib
import os
import re
import time
import urllib.parse

import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup

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


def get_image_data_url(file_path):
    """Convert a local image file to a data URL."""
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    # Determine MIME type based on file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(
        file_ext, "image/jpeg"
    )  # Default to JPEG if unknown

    return f"data:{mime_type};base64,{encoded_string}"


# Create custom HTML for advanced image viewer
def create_image_viewer_html(images, current_index):
    """Create HTML for a custom image viewer with keyboard controls and zoom using base64 images"""
    if not images:
        return "<p>No images available</p>"

    current_image = images[current_index]

    # Convert image to base64 data URL
    image_data_url = get_image_data_url(current_image)

    # Create a unique ID for the viewer div to avoid caching issues
    viewer_id = hashlib.md5(current_image.encode()).hexdigest()[:8]

    html = f"""
    <style>
        #viewer-{viewer_id} {{
            position: relative;
            width: 100%;
            height: 80vh;
            margin: 0 auto;
            text-align: center;
            overflow: auto;
        }}
        #img-container-{viewer_id} {{
            min-height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        #manga-image-{viewer_id} {{
            max-width: 100%;
            height: auto;
            transform-origin: center;
            transition: transform 0.2s;
        }}
        .controls {{
            position: fixed;
            bottom: 10px;
            left: 0;
            right: 0;
            margin: auto;
            z-index: 1000;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px;
            border-radius: 5px;
            width: fit-content;
            text-align: center;
            user-select: none;
        }}
        .controls button {{
            background: #4CAF50;
            border: none;
            color: white;
            padding: 5px 10px;
            margin: 0 5px;
            cursor: pointer;
            border-radius: 3px;
        }}
        .page-indicator {{
            margin: 0 15px;
            font-weight: bold;
        }}
        .zoom-controls {{
            margin-left: 15px;
        }}
    </style>
    
    <div id="viewer-{viewer_id}">
        <div id="img-container-{viewer_id}">
            <img id="manga-image-{viewer_id}" src="{image_data_url}" alt="Manga page">
        </div>
    </div>
    
    <div class="controls">
        <button id="prev-btn-{viewer_id}">◀ Previous</button>
        <span class="page-indicator">{current_index + 1} / {len(images)}</span>
        <button id="next-btn-{viewer_id}">Next ▶</button>
        <span class="zoom-controls">
            <button id="zoom-out-{viewer_id}">🔍-</button>
            <button id="zoom-reset-{viewer_id}">🔍100%</button>
            <button id="zoom-in-{viewer_id}">🔍+</button>
        </span>
    </div>
    
    <script>
        // Current zoom level
        let zoomLevel = 1;
        
        // Update Streamlit session state
        const sendMessageToStreamlit = (index) => {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                value: index
            }}, "*");
        }};

        const sendMessageToStreamlit_D = (index) => {{
            // Update URL parameter to trigger Streamlit rerun
            const params = new URLSearchParams(window.location.search);
            params.set('image_index', index);
            window.history.replaceState({{}}, '', '?' + params.toString());
            
            // Also send message directly to Streamlit
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                value: index
            }}, "*");
            
            // Force reload to ensure the new image is displayed
            window.parent.location.reload();
        }};
        
        // Handle keyboard navigation
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'ArrowLeft' || e.key === 'a') {{
                console.log('Left arrow pressed');
                console.log({current_index});
                console.log(e.key);
                if ({current_index} > 0) {{
                    sendMessageToStreamlit({current_index - 1});
                }}
            }} else if (e.key === 'ArrowRight' || e.key === 'd') {{
                console.log('Right arrow pressed');
                console.log({current_index});
                console.log(e.key);
                if ({current_index} < {len(images) - 1}) {{
                    sendMessageToStreamlit({current_index + 1});
                }}
            }} else if (e.key === '+' || e.key === '=') {{
                zoomIn();
            }} else if (e.key === '-') {{
                zoomOut();
            }} else if (e.key === '0') {{
                resetZoom();
            }}
        }});
        
        
        
        // Get the image element
        const image = document.getElementById('manga-image-{viewer_id}');
        
        // Zoom functions
        function zoomIn() {{
            zoomLevel = Math.min(zoomLevel + 0.1, 3);
            image.style.transform = `scale(${{zoomLevel}})`;
        }}
        
        function zoomOut() {{
            zoomLevel = Math.max(zoomLevel - 0.1, 0.5);
            image.style.transform = `scale(${{zoomLevel}})`;
        }}
        
        function resetZoom() {{
            zoomLevel = 1;
            image.style.transform = 'scale(1)';
        }}
        

        // Button click handlers
        document.getElementById('prev-btn-{viewer_id}').addEventListener('click', function() {{
            if ({current_index} > 0) {{
                sendMessageToStreamlit({current_index - 1});
            }}
        }});
        
        document.getElementById('next-btn-{viewer_id}').addEventListener('click', function() {{
            if ({current_index} < {len(images) - 1}) {{
                sendMessageToStreamlit({current_index + 1});
            }}
        }});
        // Add click handlers for zoom buttons
        document.getElementById('zoom-in-{viewer_id}').addEventListener('click', zoomIn);
        document.getElementById('zoom-out-{viewer_id}').addEventListener('click', zoomOut);
        document.getElementById('zoom-reset-{viewer_id}').addEventListener('click', resetZoom);

    </script>
    """
    return html


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
                        # Image viewer with advanced controls
                        total_images = len(chapter_images)

                        # Check if we need to initialize the image index
                        if "image_index" not in st.session_state:
                            st.session_state.image_index = 0

                        # Ensure the index is within bounds
                        if st.session_state.image_index >= total_images:
                            st.session_state.image_index = 0

                        # Use the custom HTML viewer
                        viewer_html = create_image_viewer_html(
                            chapter_images, st.session_state.image_index
                        )

                        # Get the new index from the component
                        received_value = components.html(
                            viewer_html, height=600, scrolling=True
                        )

                        # Check if we received a value from the component
                        if received_value is not None and isinstance(
                            received_value, (int, float)
                        ):
                            new_index = int(received_value)
                            if (
                                0 <= new_index < total_images
                                and new_index != st.session_state.image_index
                            ):
                                st.session_state.image_index = new_index
                                st.rerun()

                        # Display info about keyboard shortcuts
                        with st.expander("Keyboard Shortcuts"):
                            st.write(
                                """
                            - **Left Arrow** or **A**: Previous image
                            - **Right Arrow** or **D**: Next image
                            - **+** or **=**: Zoom in
                            - **-**: Zoom out
                            - **0**: Reset zoom
                            """
                            )

if __name__ == "__main__":
    # This ensures the app runs directly when executed
    pass
