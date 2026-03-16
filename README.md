# Florica

Florica is a software suite for managing botanical data, including plant taxonomy, field inventories, and species occurrences.

The project aims to provide a flexible desktop environment for botanists and researchers working with taxonomic databases and vegetation data.

Currently the first application of the suite is available:

* **Florica-Nomen** – management of plant names and taxonomic information.

Future modules will include:

* **Florica-Census** – management of plot and inventory data
* **Florica-Vista** – exploration and visualization of botanical datasets

## Installation

Florica is distributed as a Python application and should be installed using **pipx**, which installs the software in an isolated environment.

Install pipx if it is not already available:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Then install Florica directly from GitHub:

```
pipx install git+https://github.com/PhilippeBko/florica.git
```

After installation the command becomes available:

```
florica-nomen
```

## First launch

At the first launch, Florica will ask for connection parameters to a PostgreSQL server.

Required information:

* host
* port
* user
* password
* database name

If the specified database does not exist, Florica can create it automatically.

The application will also initialize the required database schema and functions.

## Features

Florica-Nomen allows users to:

* manage taxonomic names
* store accepted names and synonyms
* query external taxonomic services such as:

  * POWO
  * IPNI
  * Tropicos
* import taxonomic information from remote APIs
* maintain a local taxonomic database

## Requirements

* Python ≥ 3.10
* PostgreSQL server
* Internet connection (for external taxonomy APIs)

## Project status

Florica is currently in **early development**.

The architecture is evolving and additional modules will be released in future versions.

## Author

Philippe Birnbaum

## Source code

https://github.com/PhilippeBko/florica
