# Nido Housing Management Software

Nido is a free & open source web application that makes it easier for
multifamily housing communities, such as condominimums, neighborhood
homeowners associations, housing cooperatives, ecovillages, etc. to manage
their affairs online.

## License

Nido is licensed under the Affero GNU Public license, which can be found in
this repository. In short, it means that you can freely use, modify, and share
this code, but you are required to make your modifications publicly availible.

## Development Setup

Nido is in a very early stage of development and only availible as a `git` repository;
there are no source or binary releases at present. To install from git, make sure you
have Python version 3.9 or greater installed. After cloning the repo, you can get up
and running in three steps (all instructions are for macOS or Linux):

 - If you have [Python Poetry](https://python-poetry.org/) on your system, you can run
 `poetry install`, but if not, then `pip install -e .` will also work.
 - Launch the Nido frontend in debug mode with `flask --app nido_frontend run --debug`
 - Populate the database with fake testing data by running `./generate_mock_data.py`
