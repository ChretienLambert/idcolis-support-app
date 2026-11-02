from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="idcolis-support-app",
    version="0.1.0",
    author="IT and Digital Minds",
    author_email="noreply@example.com",
    description="ID Colis Support App with Streamlit frontend and FastAPI backend.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.12",
    packages=find_packages(include=["backend*", "frontend*"]),
    py_modules=["app"],
    install_requires=[
        "streamlit>=1.35,<2",
        "fastapi>=0.115,<1",
        "uvicorn[standard]>=0.30,<1",
        "PyJWT>=2.9,<3",
        "passlib[bcrypt]>=1.7,<2",
        "email-validator>=2.2,<3",
        "SQLAlchemy>=2.0,<3",
        "alembic>=1.13,<2",
        "pymysql>=1.1,<2",
        "python-multipart>=0.0.9,<1",
        "reportlab>=4.2,<5",
        "scikit-learn>=1.5,<2",
        "joblib>=1.4,<2",
        "httpx>=0.27,<1",
    ],
    entry_points={
        "console_scripts": [
            "idcolis-support=backend.serve:main",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Framework :: Streamlit",
        "Operating System :: Microsoft :: Windows",
    ],
)


