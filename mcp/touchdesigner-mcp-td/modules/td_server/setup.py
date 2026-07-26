from setuptools import find_packages, setup

NAME = "openapi_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python-dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="TouchDesigner API",
    author_email="",
    url="",
    keywords=["OpenAPI", "TouchDesigner API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['openapi_server=openapi_server.__main__:main']},
    long_description="""\
    OpenAPI schema for generating TouchDesigner API client code
    """
)

