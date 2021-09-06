import setuptools

with open("README.md", "r", encoding="UTF-8") as f:
    long_description = f.read()

setuptools.setup(
    name="dico-interaction",
    version="0.0.2",
    author="eunwoo1104",
    author_email="sions04@naver.com",
    description="Interaction module for dico.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dico-api/dico-interaction",
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
    install_requires=["dico-api", "aiohttp"],
    extras_require={
        "webserver": ["PyNaCl"]
    },
    classifiers=[
        "Programming Language :: Python :: 3"
    ]
)
