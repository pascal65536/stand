from setuptools import setup, find_packages

setup(
    name="flake8-myplugin",
    version="0.1.0",
    description="A custom flake8 plugin to ban print()",
    author="Your Name",
    author_email="you@example.com",
    url="https://github.com/yourname/flake8-myplugin",
    packages=find_packages(),
    entry_points={
        'flake8.extension': [
            'MP = flake8_myplugin:MyPlugin',
        ],
    },
    install_requires=[
        'flake8',
    ],
    python_requires='>=3.7',
)
