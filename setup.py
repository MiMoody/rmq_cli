from setuptools import setup, find_packages


with open("README.md") as readme_f:
    readme = readme_f.read()

setup(
    name="rmq_client",
    version="0.1.0",
    description="RabbitMQ client",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="mimoody",
    author_email="svev2369@example.com",
    install_requires=[
        "aio-pika==9.4.3",
        "aiormq==6.8.1",
        "idna==3.10",
        "multidict==6.1.0",
        "orjson==3.10.7",
        "pamqp==3.3.0",
        "propcache==0.2.0",
        "yarl==1.15.3",
    ],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
