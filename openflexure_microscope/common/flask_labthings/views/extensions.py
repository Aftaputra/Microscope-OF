"""
Top-level representation of attached and enabled Extensions
"""

from openflexure_microscope.common.flask_labthings.utilities import get_docstring
from openflexure_microscope.common.flask_labthings.schema import Schema
from openflexure_microscope.common.flask_labthings import fields

from ..resource import Resource
from ..find import registered_extensions
from ..schema import ExtensionSchema
from ..decorators import marshal_with


class ExtensionList(Resource):
    """
    List and basic documentation for all enabled Extensions
    """

    @marshal_with(ExtensionSchema(many=True))
    def get(self):
        """
        Return the current Extension forms

        .. :quickref: Extension; Get forms

        Returns an array of present Extension forms (describing Extension user interfaces.)
        Please note, this is *not* a list of all enabled Extensions, only those with associated
        user interface forms.

        A complete list of enabled Extensions can be found in the microscope state.

        """
        return registered_extensions().values()
