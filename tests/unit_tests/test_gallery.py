"""Tests that captures have the expected metadata."""


def test_gallery_thing_finds_all_providers(simulation_test_env):
    """Check the gallery identifies the correct Things that will provide data."""
    gallery = simulation_test_env.get_thing_by_name("gallery")
    snake_workflow = simulation_test_env.get_thing_by_name("snake_workflow")
    smart_scan = simulation_test_env.get_thing_by_name("smart_scan")
    camera = simulation_test_env.get_thing_by_name("camera")

    assert snake_workflow not in gallery.all_ofm_things.values()
    assert camera in gallery.all_ofm_things.values()
    assert smart_scan in gallery.all_ofm_things.values()

    assert snake_workflow not in gallery.gallery_providing_things.values()
    assert camera not in gallery.gallery_providing_things.values()
    assert smart_scan in gallery.gallery_providing_things.values()
