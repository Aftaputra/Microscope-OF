import zipfile
import shutil
import os
import glob

def create_zip_of_scan(folder_path):
    """Generate a zip file that can be downloaded, with all the scan files in it."""
    
    print("Creating zip archive of images (may take some time)...")
    zip_fname = f'{folder_path}.zip'
    
    if not os.path.isfile(zip_fname):
        shutil.make_archive(
            folder_path,
            "zip",
            folder_path,
            "images/"
        )
    
    current_zip = get_files_in_zip(zip_fname)

    files = glob.glob(folder_path + '/**/*', recursive=True)
    files = [i.split(f'{folder_path}\\')[1] for i in files]

    with zipfile.ZipFile(zip_fname, mode="a") as zip:
        for file in files:
            if file not in current_zip and ".zip" not in file:
                print(f'appending {file} to zip')
                zip.write(os.path.join(folder_path, file), arcname=file)
            else:
                print(f'{file} is already in zip')

    images_folder = os.path.join(folder_path, 'images')
    # Promote key files to the top level of the zip
    
    for fname in ["stitched_from_stage.jpg", "stitched.jpg"]:
        fpath = os.path.join(images_folder, fname)
        if os.path.exists(fpath):
            print(f'copying {fpath} to upper level')
            zip.write(fpath, arcname=fname)

def get_files_in_zip(zip_path):

    zip = zipfile.ZipFile(zip_path)
    zip = [os.path.normpath(i) for i in zip.namelist()]
    # list available files in the container, relative to the base
    return zip

create_zip_of_scan(r"G:\stitching_tests\zip_test")