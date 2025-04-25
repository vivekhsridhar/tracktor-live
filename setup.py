from setuptools import setup, find_packages

# Read dependencies from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='tracktorlive',
    version='0.1.0',
    description='Real-time low-cost tracking system.',
    author='The authors',#FIXME
    packages=find_packages(),   # Automatically finds the tracktorlive/ package
    install_requires=requirements,
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'tracktorlive=tracktorlive.__main__:main',
        ],
    },
)

