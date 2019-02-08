import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyoneer-avr",
    version="0.0.1",
    author="Justin Mutter",
    description="A python library to control Pioneer AVRs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/j-mutter/pyoneer-avr",
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
