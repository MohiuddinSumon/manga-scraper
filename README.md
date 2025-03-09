# Manga Chapter & Image Scraper

![Manga Downloader Banner](https://raw.githubusercontent.com/username/manga-scraper/main/assets/banner.png)

A streamlined Python application that allows users to download manga chapters and images from various websites. Built with Streamlit and BeautifulSoup, this tool provides an intuitive interface for both downloading and browsing manga content.

## 🌟 Features

- **Easy URL Input:** Simply paste the main manga page URL and the app handles the rest
- **Smart Chapter Detection:** Automatically finds all available chapters using customizable regex patterns
- **Selective Downloads:** Choose which specific chapters to download or use "Download All" option
- **Skip Existing Chapters:** Efficiently skip already downloaded chapters to resume interrupted downloads
- **Organized Storage:** Content saved in a clean folder structure for easy access
- **Advanced Image Viewer:** View manga with keyboard navigation, zoom controls, and full-screen capability
- **Rate Limiting:** Configurable delay between requests to be respectful to source websites
- **Responsive UI:** Real-time progress tracking and status updates

## 📋 Prerequisites

- Python 3.7+
- Internet connection

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/MohiuddinSumon/manga-scraper.git
   cd manga-scraper
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

1. Start the application:
   ```bash
   streamlit run app.py
   ```

2. In your browser (should open automatically):
   - Enter the main manga page URL
   - Provide a regex pattern to extract chapter numbers (default: `r"chapter-(\d+)"`)
   - Optional: Specify a container selector for more precise image targeting
   - Adjust delay between requests if needed
   - Click "Fetch Chapters" to detect available content
   - Select which chapters to download or use "Download All"
   - Use the "Browse" tab to view downloaded manga with enhanced viewing capabilities

### Image Viewer Controls

The enhanced image viewer supports:
- **Keyboard Navigation:** Use arrow keys (or A/D) to move between pages
- **Zoom Controls:** Use +/- keys or buttons to zoom in/out
- **Reset View:** Press 0 to reset zoom level
- **Responsive Design:** Adapts to different screen sizes

### Example Workflow

1. Input URL: `https://example-manga-site.com/manga/title`
2. Regex: `r"chapter-(\d+)"`
3. Press "Fetch Chapters"
4. Click "Download All" (it will skip any chapters already downloaded)
5. Switch to "Browse" tab to view downloaded content
6. Use keyboard shortcuts for a seamless reading experience

### Tips for Effective Use

- **Finding the right regex:** Examine the chapter URLs on the website and identify the pattern. Most sites use formats like `chapter-123` or `ch-123`.
- **Container selector (advanced):** Right-click on the manga page and "Inspect Element" to find the CSS selector for the container holding only the manga images.
- **Rate limiting:** Increase the delay for sites that might block rapid requests.
- **Skip existing:** Keep this enabled to continue interrupted downloads without duplicating content.

## 📁 Project Structure

```
manga-scraper/
├── app.py                 # Main application file
├── requirements.txt       # Project dependencies
├── LICENSE                # License information
├── README.md              # Project documentation
├── .gitignore             # Git ignore configuration
├── assets/                # Images and other assets
└── comics/                # Downloaded manga (created automatically)
    └── [Manga Title]/
        └── Chapter [Number]/
            ├── image_01.jpg
            ├── image_02.jpg
            └── ...
```

## ⚙️ Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| URL | Main page containing links to all chapters | Required |
| Regex Pattern | Regular expression to extract chapter numbers | `r"chapter-(\d+)"` |
| Container Selector | CSS selector for the element containing manga images | Optional |
| Request Delay | Time between requests (seconds) | 1.0 |
| Skip Existing Chapters | Skip chapters that have already been downloaded | Enabled |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is intended for personal use only. Please respect copyright laws and the terms of service of the websites you access. The developers of this tool are not responsible for any misuse or any consequences thereof.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- Inspired by the manga community and the need for offline reading solutions