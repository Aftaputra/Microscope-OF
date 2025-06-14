import tempfile
import os
import shutil
import logging
import random
import time

from openflexure_microscope_server.scan_directories import (
    ScanDirectoryManager,
    ScanDirectory,
    ScanInfo,
    get_files_in_zip,
)

# A global logger to pass in as an Invocation Logger
LOGGER = logging.getLogger("mock-invocation_logger")

# Use our own dir in the root temp dir not a dynamically generated one so we
# have some control of when it is deleted
BASE_SCAN_DIR = os.path.join(tempfile.gettempdir(), "scans")


def _clear_scan_dir():
    """Delete the scan dir"""
    if os.path.exists(BASE_SCAN_DIR):
        shutil.rmtree(BASE_SCAN_DIR)


def _add_fake_image(scan_dir: ScanDirectory):
    """Make a fake image on disk in the scan directory"""
    x_pos = random.randint(-100, 100)
    y_pos = random.randint(-100, 100)
    filename = f"image_{x_pos}_{y_pos}.jpg"
    filepath = os.path.join(scan_dir.images_dir, filename)
    with open(filepath, "w") as f_obj:
        f_obj.write("fake")


def _add_fake_file(scan_dir: ScanDirectory, filename: str, in_im_dir=False):
    """Make a fake file  on disk in the scan directory"""
    if in_im_dir:
        filepath = os.path.join(scan_dir.images_dir, filename)
    else:
        filepath = os.path.join(scan_dir.dir_path, filename)
    with open(filepath, "w") as f_obj:
        f_obj.write("fake")


def test_basic_directory_operations():
    """Test some basic operations

    Rather a long test but systematically iterates through some basics.
    """
    _clear_scan_dir()
    assert not os.path.isdir(BASE_SCAN_DIR)
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)
    # Check it makes the scan directory
    assert os.path.isdir(BASE_SCAN_DIR)

    # Considering a fake scan
    scan_name = "fake_scan_0001"
    scan_path = os.path.join(BASE_SCAN_DIR, scan_name)
    scan_im_dir = os.path.join(BASE_SCAN_DIR, scan_name, "images")

    # It doesn't exitist but we can check its paths
    assert not scan_dir_manager.exists(scan_name)
    assert not os.path.isdir(scan_path)
    assert scan_dir_manager.path_for(scan_name) == scan_path
    assert scan_dir_manager.img_dir_for(scan_name) == scan_im_dir

    # or a get the path of a fake file
    fake_file = scan_dir_manager.get_file_from(scan_name, "foo.zip")
    assert fake_file == os.path.join(scan_path, "foo.zip")
    # But this is none if we check it exists
    fake_file = scan_dir_manager.get_file_from(scan_name, "foo.zip", check_exists=True)
    assert fake_file is None

    # or a get the path of a fake file
    fake_file = scan_dir_manager.get_file_from_img_dir(scan_name, "bar.img")
    assert fake_file == os.path.join(scan_im_dir, "bar.img")
    # But this is none if we check it exists
    fake_file = scan_dir_manager.get_file_from_img_dir(
        scan_name, "bar.img", check_exists=True
    )
    assert fake_file is None

    # Create the dir
    scan_dir = scan_dir_manager.new_scan_dir("fake_scan")
    # This returns a ScanDirectory object
    assert isinstance(scan_dir, ScanDirectory)
    # The directory now exists as does the image directory
    assert scan_dir_manager.exists(scan_name)
    assert os.path.isdir(scan_path)
    assert os.path.isdir(scan_im_dir)

    scan_dir_manager.delete_scan(scan_name)
    assert not scan_dir_manager.exists(scan_name)
    assert not os.path.isdir(scan_path)


def test_scan_sequence_and_listing():
    """
    Check created scans are added in order and listed correctly
    """
    _clear_scan_dir()
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)
    # Make 4 scans
    scan_dir_manager.new_scan_dir("fake_scan")
    scan_dir_manager.new_scan_dir("fake_scan")
    scan_dir_manager.new_scan_dir("fake_scan")
    scan_dir_manager.new_scan_dir("fake_scan")

    # Check they exist and are numbered sequentially
    all_scans = scan_dir_manager.all_scans
    assert len(all_scans) == 4
    assert "fake_scan_0001" in all_scans
    assert "fake_scan_0002" in all_scans
    assert "fake_scan_0003" in all_scans
    assert "fake_scan_0004" in all_scans

    # Check scan data can be read for all of them
    # (more detailed scan_info tests below)
    all_scan_info = scan_dir_manager.all_scans_info()
    for scan_info in all_scan_info:
        assert isinstance(scan_info, ScanInfo)
        assert scan_info.name.startswith("fake_scan_000")
        assert scan_info.number_of_images == 0


def test_scan_name_non_sequential():
    """
    Check created scans is the correct name if the directories
    are not sequential
    """
    _clear_scan_dir()
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0001"))
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0002"))
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0003"))
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0005"))
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0007"))
    os.makedirs(os.path.join(BASE_SCAN_DIR, "fake_scan_0011"))
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)

    scan_dir = scan_dir_manager.new_scan_dir("fake_scan")
    assert scan_dir.name == "fake_scan_0012"

    all_scans = scan_dir_manager.all_scans
    assert len(all_scans) == 7
    assert "fake_scan_0001" in all_scans
    assert "fake_scan_0002" in all_scans
    assert "fake_scan_0003" in all_scans
    assert "fake_scan_0005" in all_scans
    assert "fake_scan_0007" in all_scans
    assert "fake_scan_0011" in all_scans
    assert "fake_scan_0012" in all_scans


def test_scan_info():
    """Test the scan info is correct even using fake scan data"""
    _clear_scan_dir()
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)
    scan_dir = scan_dir_manager.new_scan_dir("fake_scan")

    for i in range(17):
        _add_fake_image(scan_dir)
    info = scan_dir.scan_info()
    now = time.time()

    assert info.name == "fake_scan_0001"
    # Created and modifies in the last 5 seconds
    assert now - 5 < info.created < now
    # Created and modifies in the last 5 seconds
    assert now - 5 < info.created < now
    assert info.number_of_images == 17
    assert not info.stitch_available
    assert info.dzi is None

    # Add a fake scan and check this recognised as a stitch not a scan image
    _add_fake_file(scan_dir, "fake_scan_0001_stitched.jpg", in_im_dir=True)
    info = scan_dir.scan_info()
    assert info.number_of_images == 17
    assert info.stitch_available


def test_empty_scan_info():
    """Test the scan info is correct even if the scan is empty"""
    _clear_scan_dir()
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)
    scan_dir = scan_dir_manager.new_scan_dir("fake_scan")

    info = scan_dir.scan_info()
    now = time.time()

    assert info.name == "fake_scan_0001"
    # Created and modifies in the last 5 seconds
    assert now - 5 < info.created < now
    # Created and modifies in the last 5 seconds
    assert now - 5 < info.created < now
    assert info.number_of_images == 0
    assert not info.stitch_available
    assert info.dzi is None


def test_zipping_scan_data():
    """Test zipping the scan images with fake image data"""
    _clear_scan_dir()
    scan_dir_manager = ScanDirectoryManager(BASE_SCAN_DIR)
    scan_dir = scan_dir_manager.new_scan_dir("fake_scan")

    # Create 21 fake scan files, a fake stitch, and a fake zip
    for i in range(21):
        _add_fake_image(scan_dir)
    _add_fake_file(scan_dir, "fake_scan_0001_stitched.jpg", in_im_dir=True)
    _add_fake_file(scan_dir, "zipfile.zip")

    # zip the directory without setting as the final version. It should only
    # zip the 21 scan images
    zip_fname = scan_dir.zip_files()
    zip_files = get_files_in_zip(zip_fname)
    assert len(zip_files) == 21

    # Zip again with final version on and there should be 22 images
    scan_dir.zip_files(final_version=True)
    zip_files = get_files_in_zip(zip_fname)
    assert len(get_files_in_zip(zip_fname)) == 22
    # Check the zips are not in the zip
    for file in zip_files:
        assert not file.endswith(".zip")
