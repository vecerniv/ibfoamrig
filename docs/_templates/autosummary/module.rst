{{ fullname | escape | underline }}

.. automodule:: {{ fullname }}
   :no-members:

{% if classes %}
.. rubric:: Classes

.. autosummary::
   :toctree:
   :template: autosummary/class.rst
{% for item in classes %}
   {{ item }}
{%- endfor %}
{% endif %}

{% if functions %}
.. rubric:: Functions

.. autosummary::
   :toctree:
{% for item in functions %}
   {{ item }}
{%- endfor %}
{% endif %}

{% if exceptions %}
.. rubric:: Exceptions

.. autosummary::
   :toctree:
   :template: autosummary/class.rst
{% for item in exceptions %}
   {{ item }}
{%- endfor %}
{% endif %}

{% if attributes %}
.. rubric:: Type aliases and constants

.. autosummary::
   :toctree:
{% for item in attributes %}
   {{ item }}
{%- endfor %}
{% endif %}
