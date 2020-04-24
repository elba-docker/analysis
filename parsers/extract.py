"""
Contains functions used to recursively extract
"""

import tarfile
import os
import platform
from multiprocessing import cpu_count, Pool


def get_unique_name(archive_path):
    """
    Gets the unique and deterministic "checksum" name of the archive to use for in-place extraction
    caching
    """

    filename = os.path.basename(archive_path)
    fake_checksum = os.path.getsize(archive_path)
    return f"{filename}_{str(fake_checksum)}"


def get_all_files(dir_path, ext=None, deep=True):
    """
    Gets all files with the given extension (optional)
    """

    try:
        shallow_list = os.listdir(dir_path)
    except:
        return []
    allFiles = list()
    for entry in shallow_list:
        fullPath = os.path.join(dir_path, entry)
        if os.path.isdir(fullPath):
            if deep:
                allFiles.extend(get_all_files(fullPath, ext=ext))
        else:
            if (ext is not None and fullPath.endswith(ext)) or ext is None:
                allFiles.append(fullPath)
    return allFiles


def extract_all(root, working_dir=None):
    """
    Extracts all found archives from root into working_dir recursively, returning a
    lazy-parsing ORM root object once done
    """

    # fold default
    if working_dir is None:
        working = f"{root}/results/"

    working_abs = os.path.abspath(working_dir)
    all_unextracted_archives = [archive for archive in get_all_files(root, ext=".tar.gz")
                                if not has_been_extracted(archive, working_abs)]
    if all_unextracted_archives:
        num_workers = min(cpu_count(), len(all_unextracted_archives))
        print(
            f"Extracting {len(all_unextracted_archives)} top level archives on {num_workers} workers")
        archives_with_working_dir = zip(all_unextracted_archives,
                                        [working_abs] * len(all_unextracted_archives))
        with Pool(num_workers) as pool:
            for _ in pool.imap_unordered(subprocess_extract, archives_with_working_dir):
                pass

    # Return list of all extracted archives
    return get_all_files(root, ext=".tar.gz")


def subprocess_extract(path_tuple):
    """
    Entry function of multiprocessing worker processes
    """

    (archive_path, working_dir) = path_tuple
    pid = os.getpid()
    print(f"Extracting top level archive {archive_path} to {working_dir} on process PID {pid}")
    extract_recursive(archive_path, working_dir)


def has_been_extracted(archive_path, working_dir):
    """
    Gets whether the given archive has been extracted before to its extraction cache directory
    within the given working directory
    """

    archive_extracted_name = get_unique_name(archive_path)
    extracted_path = os.path.join(working_dir, archive_extracted_name)
    return os.path.exists(extracted_path)


def extract_recursive(archive_path, working_dir="./working"):
    """
    Recursively extracts the given .tar.gz archive, extracting to a unique and deterministic
    folder name inside of working_dir. If the folder already exists, then searches the folder
    and recursively continues
    """

    extracted_path = os.path.join(working_dir, get_unique_name(archive_path))
    if not os.path.exists(extracted_path):
        print(f"Extracting {archive_path} to {extracted_path}...", end=" ")
        with tarfile.open(archive_path) as tar_file:
            tar_file.extractall(extracted_path)
        print("done")

    # Now, search for all .tar.gz and .gz files in folder
    all_archives = get_all_files(extracted_path, ext=".tar.gz")
    all_gzipped = [file for file in get_all_files(extracted_path, ext=".gz")
                   if not file.endswith(".tar.gz")]

    # Extract all gzip files
    if all_gzipped:
        os.system('gunzip -k ' + " ".join(all_gzipped))

    # Extract all archives
    if all_archives:
        for archive in all_archives:
            extract_recursive(archive, working_dir=os.path.dirname(archive))

