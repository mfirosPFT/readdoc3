# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


import os
import pathlib
import sys
# sys.path.insert(0, pathlib.Path(__file__).parents[2].resolve().as_posix())

sys.path.insert(0, os.path.abspath('../functions'))
project = 'DCinema Distribution AWS Resources'
copyright = '2023, Prime Focus'
author = 'Firos M'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon",
              "sphinx.ext.todo", "sphinx.ext.viewcode", 'sphinx.ext.autosummary', 'sphinx.ext.autosectionlabel']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']


latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    # keep code blocks background grey and syntax highlighted
    # try adding good fonts
    'fncychap': '\\usepackage[Bjornstrup]{fncychap}',
    'fontpkg': '\\usepackage{times}',
    'figure_align': 'htbp',




}
