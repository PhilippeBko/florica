import os
import sys

# Ajouter le chemin vers src pour que Sphinx voie ton package
sys.path.insert(0, os.path.abspath('../../src'))
autodoc_mock_imports = ["PyQt5", "PyQt6", "PySide2", "PySide6"]
autodoc_member_order = 'groupwise'




# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'florica'
copyright = '2026, Philippe Birnbaum'
author = 'Philippe Birnbaum'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
