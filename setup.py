from setuptools import setup, find_packages

setup(
    name="story_agents",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "aiosqlite==0.19.0",
        "pysqlite3==2.6.0",
        "sqlcipher3-binary==0.5.0",
        "python-json-logger==2.0.7",
        "asyncio==3.4.3",
        "cryptography==41.0.1",
        "alembic==1.12.0",
        "pytest==7.4.0",
        "pytest-asyncio==0.21.1"
    ],
    python_requires=">=3.8",
) 