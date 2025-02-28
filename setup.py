from setuptools import setup

setup(
    name="codemap",
    version="0.1.0",
    py_modules=["codemap"],
    install_requires=[
        "windows-curses;platform_system=='Windows'"
    ],
    entry_points={
        "console_scripts": [
            "codemap=codemap:main",
        ],
    },
) 