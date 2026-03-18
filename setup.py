from setuptools import setup, find_packages

setup(
    name="youtube-extrator",
    version="1.0.0",
    description="Vigiar e Punir - Detector de conteúdo +18 em canais do YouTube",
    author="Antigravity",
    packages=find_packages(),
    install_requires=[
        "requests",
        "aiohttp",
        "scrapetube",
    ],
    entry_points={
        "console_scripts": [
            "yt-extrator=main:async_main",
        ],
    },
    python_requires=">=3.8",
)
