"""
Setup configuration for XML Database Extraction system.
Use this for:
- Creating a Distributable Package
- Professional Deployment (Installing as a system service, Deploying to production servers)

If you're just setting up another development environment, consider using `pip install -e .` instead.

For Distributable Package:
- python setup.py sdist bdist_wheel
    (Creates installable .whl files in dist/ folder)
"""

from setuptools import setup, find_packages
from pathlib import Path

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
    name="xml_extractor",
    version="1.6.4",
    author="XML Extractor Team",
    description="Configurable high-performance tool for migrating XML to database relational structures.",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: Pre-Production",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    python_requires=">=3.8",
    install_requires=main_requirements,
    extras_require={
        "dev": dev_requirements,
        "optional": optional_requirements,
    },
    entry_points={
        "console_scripts": [
            "production_processor=xml_extractor.cli:main",
            "run_production_processor=xml_extractor.cli:main",
            "xml_extractor=xml_extractor.cli:main",
        ],
    },
)