# timely
Time tracking tool aggregating data from Microsoft Outlook (365), [Kapow Punch Clock](https://gottcode.org/kapow/) and [Ezeit](https://www.hamburg.de/politik-und-verwaltung/behoerden/personalamt/landesbetriebe/zentrum-fuer-personaldienste/ezeit-216056) (time tracking system for the employees of the free and hanseatic city of Hamburg, Germany)

## About

This is an experimental app built with the Python framework FAST-API. 

The primary goal is to apply and deepen my knowledge of basic web development while experimenting with the Fast-API framework, the pydantic library and pyinstaller. 

The secondary goal is to create an app that my coworkers can use to aggregate time tracking data from multiple sources, facilitating the cost accounting in SAP.

While development is (mostly) approached as if the program was a web-app, the intended distribution is a local executable. As the data processed and stored by the application is sensitive, a productive deployment would require identity and access management, which is out of scope for this project.

For now, the imported data is assumed to be in German.