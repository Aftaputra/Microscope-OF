Marshaling data
===============

Introduction
------------

- Define marshaling
- Why marshal objects?

- Marshmallow library
- Marshmallow schema and fields
    - Schema class
    - Schema dictionaries

- Using schema in ``@marshal_with``
- Using schema in ``@use_args``

In the previous section we saw how to use fields to document the expected request body for simple requests, in which a single argument is required. By making use of Marshmallow schemas, we can allow more complex requests containing many parameters of different types. The parsed request parameters are then passed to the view function as a positional argument (as before), in the form of a dictionary. 

For example, your ``@use_args`` decorator may look like:

.. code-block:: python

    @use_args({
        "name": fields.String(required=True),
        "age": fields.Integer(required=True),
        "job": fields.String(required=False, missing="Unknown")
    })

A compatible request body, in JSON format, may look like:

.. code-block:: json

    {
        "name": "John Doe",
        "age": 45,
        "job": "Python developer"
    }

This JSON data is the parsed, converted into a Python dictionary, and passed as an argument. Retreiving the data from within your view function may therefore look like:

.. code-block:: python

    @use_args({
        "name": fields.String(required=True),
        "age": fields.Integer(required=True),
        "job": fields.String(required=False, missing="Unknown")
    })
    def post(self, args):
        name = args.get("name")  # Returns "John Doe", type str
        age = args.get("age")  # Returns 45, type int
        job = args.get("job")  # Returns "Python developer", type str


- Example (from ``03_marshaling_data.py``)
