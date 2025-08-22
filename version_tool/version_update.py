"""
A little useful tool to help me keep track of my update numbers, for archiving and release purposes.
This Python script and batch file were developed by Aerox Software.

All code in this folder ("version_tool") is free and unencumbered software released into the public domain.
Refer to LICENSE file if you have any concerns.
"""

import re
import sys
import subprocess

file_path = 'build_version_info.bat'

def increment_version(version_part):
    """
    Increments the specified version number (MAJOR, MINOR, PATCH, or BUILD) in build_version_info.bat.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)

    # Use a regular expression to find the version numbers
    major_match = re.search(r"set MAJOR=(\d+)", content)
    minor_match = re.search(r"set MINOR=(\d+)", content)
    patch_match = re.search(r"set PATCH=(\d+)", content)
    build_match = re.search(r"set BUILD=(\d+)", content)

    if not all([major_match, minor_match, patch_match, build_match]):
        print("Error: Could not find all MAJOR, MINOR, PATCH, and BUILD variables in the file.")
        sys.exit(1)

    major = int(major_match.group(1))
    minor = int(minor_match.group(1))
    patch = int(patch_match.group(1))
    build = int(build_match.group(1))

    if version_part == 'major':
        major += 1
        minor = 0
        patch = 0
        build = 0
    elif version_part == 'minor':
        minor += 1
        patch = 0
        build = 0
    elif version_part == 'patch':
        patch += 1
        build = 0
    elif version_part == 'build':
        build += 1
    else:
        print(f"Error: Invalid argument '{version_part}'. Use 'major', 'minor', 'patch', or 'build'.")
        sys.exit(1)

    # Replace the old version numbers with the new ones
    new_content = re.sub(r"set MAJOR=\d+", f"set MAJOR={major}", content, count=1)
    new_content = re.sub(r"set MINOR=\d+", f"set MINOR={minor}", new_content, count=1)
    new_content = re.sub(r"set PATCH=\d+", f"set PATCH={patch}", new_content, count=1)
    new_content = re.sub(r"set BUILD=\d+", f"set BUILD={build}", new_content, count=1)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.write(new_content)

    print(f"Version updated to: {major}.{minor}.{patch}.{build}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python version_update.py [major|minor|patch|build]")
        sys.exit(1)

    version_part_to_increment = sys.argv[1].lower()
    increment_version(version_part_to_increment)
    
    batcmd = subprocess.run(file_path, shell=True, check=True, capture_output=True, text=True)
    print(file_path, "'s output:")
    print(batcmd.stdout)
    print("Errors, if any:")
    print(batcmd.stderr)