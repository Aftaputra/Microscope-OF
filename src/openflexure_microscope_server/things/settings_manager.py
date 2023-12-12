"""
OpenFlexure Settings Management

This module provides some settings management across the other Things, and
for code that currently lives in clients but needs to persist settings on
the server.
"""
from collections.abc import Mapping
from typing import Any, Mapping, MutableMapping, Optional, Sequence
from fastapi import HTTPException
from labthings_fastapi.dependencies.metadata import GetThingStates
from labthings_fastapi.thing import Thing
from labthings_fastapi.decorators import thing_action, thing_property
from pydantic import BaseModel


def recursive_update(old_dict: MutableMapping, update: Mapping):
    """Update a dictionary recursively"""
    for k, v in update.items():
        if isinstance(v, Mapping):
            if (
                k in old_dict 
                and isinstance(old_dict[k], MutableMapping)
            ):
                recursive_update(old_dict[k], v)
            else:
                old_dict[k] = dict(**v)
        else:
            old_dict[k] = v


def nested_dict_get(data: dict, key: Sequence[str], create=False) -> Any:
    """Index a dict-of-dicts with a sequence of strings"""
    subdict = data
    for k in key:
        if k not in subdict and create:
            subdict[k] = {}
        subdict = subdict[k]
    return subdict


class SettingsManager(Thing):
    @thing_property
    def external_metadata(self) -> Mapping:
        """External metadata stored in the server's settings"""
        return self.thing_settings.get("external_metadata", {})
    
    @thing_action
    def update_external_metadata(self, data: Mapping, key: Optional[str] = None) -> None:
        """Add or replace keys in the external metadata.
        
        The data supplied will be merged into the existing dictionary
        recursively, i.e. if a key exists, it will be added to rather than
        replaced.

        If a key is supplied, we will treat `data` as being relative to that
        key, i.e. calling this action with `data={"a":1 }, key="foo/bar"` is
        equivalent to calling it with `data={"foo": {"bar": {"a": 1}}}`.
        """
        metadata = self.external_metadata
        subdict = metadata
        # If we're operating only on a part of the dict, make sure
        # that key exists, and find it.
        if key:
            subdict = nested_dict_get(subdict, key.split("/"), create=True)
        recursive_update(subdict, data)
        self.thing_settings["external_metadata"] = metadata

    @thing_action
    def delete_external_metadata(self, key: str) -> None:
        """Delete a key from the stored metadata.
        
        The key may contain forward slashes, which are understood to separate
        levels of the dictionary - i.e. `'a/c'` will remove the `c` key from a
        dictionary that looks like: `{'a': {'c': 1}, 'b': {'d': 2}}`
        """
        metadata = self.external_metadata
        try:
            subdict = nested_dict_get(metadata, key.split("/")[:-1])
            del subdict[key.split("/")[-1]]
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail="The specified key '{key}' was not found"
            )
        self.thing_settings["external_metadata"] = metadata
    
    @thing_action
    def get_things_state(self, metadata_getter: GetThingStates) -> Mapping:
        """Metadata summarising the current state of all Things in the server"""
        return metadata_getter()

    @thing_property
    def external_metadata_in_state(self) -> Sequence[str]:
        """A list of strings that are included in the "state" metadata"""
        return self.thing_settings.get("external_metadata_in_state", [])
    @external_metadata_in_state.setter
    def external_metadata_in_state(self, keys: Sequence[str]):
        """Set the keys from external metadata that are returned in state"""
        self.thing_settings["external_metadata_in_state"] = keys

    @property
    def thing_state(self) -> Mapping:
        state = {}
        metadata = self.external_metadata
        for k in self.external_metadata_in_state:
            try:
                kl = k.split("/")
                v = nested_dict_get(metadata, kl)
                subdict = nested_dict_get(state, kl[:-1], create=True)
                subdict[kl[-1]] = v
            except KeyError:
                continue
        return state