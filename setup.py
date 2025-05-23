from setuptools import setup, find_packages

setup(
    name="foxhole-automated-quartermaster",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy>=2.0.0",
        "loguru>=0.7.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "aiosqlite>=0.19.0",
    ],
) 