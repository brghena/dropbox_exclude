#! /usr/bin/env python3

# iterate through Dropbox, excluding desired files and directories but keeping
#   their contents.
# this only works on linux

################
## Configuration
################

# root of dropbox
dropbox_root = '/home/brghena/Dropbox/scratch'

# folders to be excluded from dropbox
exclude_dirs = ['node_modules', 'build', '_build', 'bower_components']

# files to be exlcuded from dropbox
exclude_files = []

# directories to never expand into
avoid_dirs = ['.git', '.svn']

# scratch space for moving files and folders
scratch_dir = "/tmp/dropbox_ignore/"

################


import os
import time
from sh import mv
try:
    from sh import dropbox
except ImportError:
    print("Cannot find dropbox executable...")
    exit(1)

# recursively search for excluded files and directories, adding them to the
#   dropbox exclude list (if not already added) but preserving their contents
def main ():
    # moe to dropbox root
    os.chdir(dropbox_root)

    # ensure scratch isn't with dropbox
    #   that would cause everything to break
    if in_directory(scratch_dir, dropbox_root):
        print("Error: scratch space cannot be within dropbox")
        print("\t" + str(scratch_dir) + " is within " + str(dropbox_root))
        exit(1)

    # make scratch space if not existing
    os.makedirs(scratch_dir, exist_ok=True)

    # ensure the scratch space is empty
    if os.listdir(scratch_dir) != []:
        print("Error: scratch directory is not empty")
        exit(1)

    # walk to directory tree
    #   do not follow symlinks
    for root, dirs, files in os.walk(dropbox_root, True, error_func, False):

        # check for directories to avoid:
        for avoid in avoid_dirs:
            if avoid in dirs:
                dirs.remove(avoid)

        # check for excluded directories
        for excl in exclude_dirs:
            if excl in dirs:
                file_path = os.path.join(root, excl)
                remove_from_dropbox(file_path)

                # do not recurse into that directory
                dirs.remove(excl)

        # check for excluded files
        for excl in exclude_files:
            if excl in files:
                file_path = os.path.join(root, excl)
                remove_from_dropbox(file_path)

# determine if a file is within a directory
#   http://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory
def in_directory(file_path, dir_path):
    #make both absolute    
    file_path = os.path.realpath(file_path)
    dir_path = os.path.join(os.path.realpath(dir_path), '')

    #return true, if the common prefix of both is equal to directory
    #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return (os.path.commonprefix([file_path, dir_path]) == dir_path)

# print errors occurring during director walk, abort run
def error_func (err):
    print("Error walking directories: " + str(err))
    raise err

# exclude a file/folder from dropbox but keep its contents
def remove_from_dropbox (file_path):
    print(file_path)
    file_name = os.path.basename(os.path.normpath(file_path))
    file_dir = os.path.dirname(os.path.normpath(file_path))

    # check if file is already excluded from dropbox, if so our task is done
    if dropbox_check(file_path):
        print("\tAlready excluded")
        return

    # move file to scratch space
    print("\tMoving file")
    result = mv("-n", file_path, scratch_dir)
    if result != "":
        print("Error: mv out had a problem")
        print(result)
        exit(1)

    # wait for dropbox to sync
    print("\tWaiting for sync")
    dropbox_sync(file_path)

    # exclude file from dropbox
    print("\tExcluding from dropbox")
    dropbox_exclude(file_path)

    # move file back to original location
    print("\tRestoring file")
    scratch_file = os.path.join(scratch_dir, file_name)
    result = mv("-n", scratch_file, file_dir)
    if result != "":
        print("Error: mv back had a problem")
        print(result)
        exit(1)

    # finished with file
    print("")

# check if a file is already excluded from dropbox
def dropbox_check (file_path):
    # get files excluded from dropbox
    excludes = dropbox("exclude", "list").split()[1:]
    excludes = [os.path.join(dropbox_root, exclude) for exclude in excludes]

    return (file_path in excludes)

# wait for dropbox to sync before returning
def dropbox_sync (file_path):

    # wait until dropbox has completed syncing
    result = ""
    while result != "Up to date\n":
        # sleep ten seconds between invocations to not overwhelm dropbox
        #   also wait ten seconds before checking with dropbox to begin with
        time.sleep(10)

        # check if dropbox is still syncing
        result = dropbox("status")

# exclude a file from dropbox
def dropbox_exclude (file_path):
    result = dropbox("exclude", "add", file_path)
    if result.split()[0] != "Excluded:":
        print("Error attempting to exclude " + str(file_path))
        print(result)
        exit(1)


if __name__ == "__main__":
    main()

