from setuptools import setup, find_packages

setup(
    name="FlaskSpark",
    version="0.1.0",
    description="FlaskSpark is a lightweight and customizable Flask boilerplate designed to ignite your web application development process.",
    author="berofa",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=2.0",
        "flask_sqlalchemy",
        "flask_migrate",
        "flask_login",
        "python-dotenv"
    ],
)
