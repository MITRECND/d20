from setuptools import setup, find_packages

GAME_ENGINE_VERSION_RAW: str

# Import GAME_ENGINE_VERSION_RAW
# TODO XXX find a more elegant way of tracking versions
with open('d20/version.py') as f:
    exec(f.read())

setup(name="d20",
      version=GAME_ENGINE_VERSION_RAW,  # noqa
      description="d20",
      author="MITRE",
      author_email="",
      python_requires=">=3.6",
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
