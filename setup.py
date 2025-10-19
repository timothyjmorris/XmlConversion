"""Setup configuration for XML Database Extraction system."""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Separate main requirements from development requirements
main_requirements = []
dev_requirements = []
optional_requirements = []

for req in requirements:
    if any(dev_pkg in req for dev_pkg in ["pytest", "black", "flake8", "mypy"]):
        dev_requirements.append(req)
    elif "Optional:" in req:
        optional_requirements.append(req.replace("# Optional: For advanced XML processing", "").replace("# Optional: For progress bars and CLI", "").strip())
    elif not req.startswith("#"):
        main_requirements.append(req)

setup(
    name="xml-database-extractor",
    version="1.0.0",
    author="XML Extractor Team",
    description="High-performance tool for extracting XML data from database text columns",
    long_description="A configurable data migration tool that processes XML content stored in database text columns and transforms it into normalized relational structures.",
    long_description_content_type="text/plain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=main_requirements,
    extras_require={
        "dev": dev_requirements,
        "optional": optional_requirements,
    },
    entry_points={
        "console_scripts": [
            "xml-extractor=xml_extractor.cli:main",
        ],
    },
)