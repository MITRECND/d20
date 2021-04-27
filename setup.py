from os import path
from setuptools import setup, find_packages

GAME_ENGINE_VERSION_RAW: str

cwd = path.abspath(path.dirname(__file__))
# Import GAME_ENGINE_VERSION_RAW
# TODO XXX find a more elegant way of tracking versions
with open(path.join(cwd, 'd20', 'version.py')) as f:
    exec(f.read())


with open(path.join(cwd, 'README.md')) as f:
    long_description = f.read()


setup(name="d20-framework",
      version=GAME_ENGINE_VERSION_RAW,  # noqa
      description="Automated Static Analysis Framework",
      long_description=long_description,
      long_description_content_type='text/markdown',
      author="MITRE",
      author_email="",
      url="https://github.com/MITRECND/d20",
      python_requires=">=3.6",
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Topic :: Security',
      ],
      install_requires=[
          'python-magic',
          'ssdeep',
          'pyyaml>=5.1,<5.2',
          'requests',
          'packaging',
          'cerberus',
          'texttable'
      ],
      packages=find_packages(exclude=("d20.tests",)),
      entry_points={'console_scripts':
                    ['d20=d20.Manual.Entry:main',
                     'd20-shell=d20.Manual.Entry:shellmain']}
      )
