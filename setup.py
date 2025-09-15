"""Setup script for weather_decoder package"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="weather-decoder",
    version="1.0.7",
    author="Justin",
    description="A comprehensive METAR and TAF decoder for aviation weather reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "decode-metar=weather_decoder.cli.metar_cli:main",
            "decode-taf=weather_decoder.cli.taf_cli:main",
        ],
    },
    keywords="metar taf aviation weather meteorology parsing decoder",
    project_urls={
        "Source": "https://github.com/6639835/metar-taf-decoder",
        "Bug Reports": "https://github.com/6639835/metar-taf-decoder/issues",
    },
)
