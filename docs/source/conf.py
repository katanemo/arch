# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Arch'
copyright = '2024, Katanemo Labs, Inc'
author = 'Katanemo Labs, Inc'
release = '0.1-beta'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


root_doc = 'root'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',    # For generating documentation from docstrings
    'sphinx.ext.napoleon',   # For Google style and NumPy style docstrings
    'sphinx_copybutton',
    'sphinx.ext.viewcode',
]

# Paths that contain templates, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and directories
# to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_favicon = '_static/favicon.ico'

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_book_theme'  # You can change the theme to 'sphinx_rtd_theme' or another of your choice.

# Specify the path to the logo image file (make sure the logo is in the _static directory)
html_logo = '_static/img/arch-nav-logo.png'

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

#html_style = 'css/arch.css'
