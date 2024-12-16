from setuptools import setup, find_packages

setup(
    name="listenbrainz-moode-scrobbler",
    version="0.1.0",
    author="StreamDigger",
    description="ListenBrainz scrobbler for moOde audio player",
    license="GNU General Public License v3.0",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'watchdog>=3.0.0',
        'liblistenbrainz>=0.5.0'
    ],
    package_data={
        'src': ['*.json'],
    }
) 