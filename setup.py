import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyoneer_vsx",
    version="0.0.2",
    author="Justin Mutter",
    description="A python library to control Pioneer VSX AVRs over telnet",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/j-mutter/pyoneer_vsx",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Home Automation",
        "Topic :: Multimedia :: Sound/Audio",
    ],
)
