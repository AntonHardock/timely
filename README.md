# timely
Time tracking tool aggregating data from Microsoft Outlook (365), [Kapow Punch Clock](https://gottcode.org/kapow/) and [Ezeit](https://www.hamburg.de/politik-und-verwaltung/behoerden/personalamt/landesbetriebe/zentrum-fuer-personaldienste/ezeit-216056) (time tracking system for the employees of the free and hanseatic city of Hamburg, Germany)

## About

This is an experimental app built with the Python framework FAST-API. 

The primary goal is to apply and deepen my knowledge of basic web development while experimenting with the Fast-API framework, the pydantic library and pyinstaller. 

The secondary goal is to create an app that my coworkers can use to aggregate time tracking data from multiple sources, facilitating the cost accounting in SAP.

While development is (mostly) approached as if the program was a web-app, the intended distribution is a local executable. As the data processed and stored by the application is sensitive, a productive deployment would require identity and access management, which is out of scope for this project.

For now, the imported data is assumed to be in German.

## Dev Setup

### Prerequisites
This project uses [pixi](https://pixi.prefix.dev/latest/) for managing dependencies.
It downloads and resolves packages from conda-forge by default.
One nice feature is that packages from conda-forge and pypi can be integrated seamlessly.

### Run app for development

Open a terminal where the pixi command is available and run the application entrypoint as a regular python script:

```shell
pixi run python app/main.py
```

### Bundle app using pyinstaller

```shell
pixi run pyinstaller timely.spec
```

The file `timely.spec` contains project specific settings.
Note that it uses `pyinstaller.py` as an entrypoint instead of `app/main.py`.
This is to avoid some module import issues in the frozen application.
It also contains some additional settings when bundling under Windows.

### Note using pyinstaller with conda packages

For this project, all dependencies except for the python interpreter come from pypi.
The reason for this is the intended distribution through pyinstaller.
Depending on the packages in use, one can run into some issues when those packages
were installed from conda-forge. I had some issues with .dll files that
the pyinstaller analyzer could not find, even when using additional hooks or explicit
path mappings in the .spec file. Once I reinstalled all dependencies from pypi, pyinstaller worked properly.

In case you want to initiate the environment from scratch:

- Delete all pixi related files as well as /build and /dist folders
in case you already tried to execute pyinstaller.
- Run following commands:
```shell
# initiate pixi project
pixi init

# python interpreter (version as in pixi.toml) has to be added first so that packages from pypi can be resolved
pixi add python==xyz

# add all packages as stated in pixi.toml file with --pypi flag
pixi add --pypi fastapi==xyz ...
```