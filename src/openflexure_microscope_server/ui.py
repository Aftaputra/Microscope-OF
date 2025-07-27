"""Functionality for communicating the required user interface for a thing."""

from pydantic import BaseModel


def action_button_for(action, **kwargs):
    """Create an action button for the specified Thing Action.

    :param action: The thing action to create a button for.
    :param kwargs: Any attribute of `ActionButton` except for ``thing`` or ``action``.
    """
    thing = action.args[0]
    thing_path = thing.path.strip("/")
    action_name = action.func.__name__
    return ActionButton(thing=thing_path, action=action_name, **kwargs)


class ActionButton(BaseModel):
    """The data required for creating an actionButton in Vue.

    Currently this cannot be used to submitData, or to submitOnEvent.
    """

    thing: str
    """The Thing "path" for the Thing instance."""

    action: str
    """The name of the action to be triggered."""

    poll_interval: int = 1
    """The interval for polling in seconds."""

    submit_label: str = "Submit"
    """The label for the action button."""

    can_terminate: bool = True
    """Specify whether the action can be terminated."""

    requires_confirmation: bool = False
    """Specify whether a confirmation modal is needed."""

    confirmation_message: str = "Start task?"
    """The message for the confirmation modal."""

    button_primary: bool = True
    """Specify whether the button is styled as a primary button."""

    modal_progress: bool = False
    """Specify whether to show a progress modal."""

    notify_on_success: bool = False
    """Specify whether to a notification on successful completion."""

    success_message: str = "Success!"
    """The message to show on successful completion."""
