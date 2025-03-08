from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="manga-scraper",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Streamlit app to download and browse manga chapters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MohiuddinSumon/manga-scraper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "streamlit>=1.18.0",
        "requests>=2.28.1",
        "beautifulsoup4>=4.11.1",
        "Pillow>=9.2.0",
    ],
    entry_points={
        "console_scripts": [
            "manga-scraper=app:main",
        ],
    },
)
