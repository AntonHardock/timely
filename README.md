# timely
Time tracking tool aggregating data from Microsoft Outlook (365), [Kapow Punch Clock](https://gottcode.org/kapow/) and [Ezeit](https://www.hamburg.de/politik-und-verwaltung/behoerden/personalamt/landesbetriebe/zentrum-fuer-personaldienste/ezeit-216056) (time tracking system for the employees of the free and hanseatic city of Hamburg, Germany)

## About

This is an experimental app built with the Python framework [FastAPI](https://fastapi.tiangolo.com/) . 

The primary goal is to apply and deepen my knowledge of basic web development while experimenting with FastAPI, pydantic and pyinstaller. 

The secondary goal is to create an app that my coworkers can use to aggregate time tracking data from multiple sources, facilitating the cost accounting in SAP.

While development is (mostly) approached as if the program was a web-app, the intended distribution is a local executable. As the data processed and stored by the application is sensitive, a productive web-deployment would require identity and access management among other things, which is out of scope for this project.

For now, the imported data is assumed to be in German, since EZeit is a tool specific to my workplace.
However, timely is designed to be expandable for new/alternative data sources.
The aggregation of time data can be configured by the user.

## Setup

### Prerequisites
This project uses [pixi](https://pixi.prefix.dev/latest/) for managing dependencies.
It downloads and resolves packages from conda-forge by default.
One nice feature is that packages from conda-forge and pypi can be integrated seamlessly.

### Run app for development

Open a terminal where the pixi command is available and run the application entrypoint as a regular python script:

```shell
pixi run python app/main.py
```

The app will run on localhost, port 8000: <http://127.0.0.1:8000/>

By default, the underlying web framework exposes an OpenAPI document
describing all endpoints: <http://127.0.0.1:8000/docs>

### Create an executable with pyinstaller

Inside the project root path, build the executable as follows:

```shell
pixi run pyinstaller timely.spec
```

The file `timely.spec` contains all project specific settings.
This will create the folders `build` and `dist`.
To start the application, run:

```shell
./dist/timely/timely.exe
```

The app will run on localhost, port 8000: <http://127.0.0.1:8000/>

The main configuration file will be bundled to `dist/_internal/configs/config.json`.
Upon first initiation, a sqlite file is created for data persistence: `dist/db`.
You can move and rename the database - be sure to adjust the `config.json` accordingly.

Note that `timely.spec` uses `pyinstaller.py` as an entrypoint instead of `app/main.py`.
This is to avoid some module import issues in the frozen application.
It also contains some additional settings when bundling under Windows.

## Further information

### Why this particular stack was chosen

As the name suggests, FastAPI focuses on (REST) APIs.
It is commonly paired with [uvicorn](https://uvicorn.dev/), an ASGI server suited for scaling I/O-heavy applications.

From [Pandy Knight's talk at PyOhio conference 2023](https://www.youtube.com/watch?v=zR0qpPTvosI),
I've learned that these tools can be easily extended into a Python-only fullstack.
While the talk is centered around incorporating HTMX for dynamic page rendering, my use case is simpler.

The frontend merely consists of forms, tables and potentially some graphs.
Serving static html pages does the job just fine in this context.
Especially as the app is supposed to run locally.
Incorporating Jinja2 to handle html templates is straight forward.

Users can import time tracking data from various sources, including manually edited csv files.
Therefore, data validation is crucial. This is where FastAPI shines by integrating pydantic so elegantly.
With this toolset, implementing data validation becomes relatively simple.

I also tested how to bring vanilla JavaScript into the mix.
In this setup, .js files are simply served as static resources, alongside the CSS.
Check out `javascript/local_time.js` - a simple script adjusting form fields using the client's local time.
Of course, a server-side implementation would be even simpler.
However, the purpose is to demonstrate where to add JavaScript functionality in this setup.
This allows for greater flexibility when introducing more complex frontend functionality.

### Issues when using pyinstaller with conda packages

For this project, all dependencies are installed from pypi.
The reason for this is the intended distribution through pyinstaller.
Depending on the packages in use, one can run into some issues when those packages
were installed from conda-forge. I had some issues with .dll files that
the pyinstaller analyzer could not find, even when using additional hooks or explicit
path mappings in the .spec file. It appears that there are less such issues with pypi as source.

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