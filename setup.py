from setuptools import setup, find_packages

setup(
    name="agent-forge",
    version="1.0.0",
    description="Create and manage Claude-powered AI agents with up to 5 tools each",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="AgentForge",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.25.0",
    ],
    extras_require={
        "dev": ["pytest", "black", "mypy"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
