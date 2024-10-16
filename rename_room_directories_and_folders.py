import os

# Dictionary to map numbers to words
number_to_word = {
    "00": "zero",
    "01": "one",
    "02": "two",
    "03": "three",
    "04": "four",
    "05": "five",
    "06": "six",
    "07": "seven",
    "08": "eight",
    "09": "nine",
    "10": "ten",
    "11": "eleven",
    "12": "twelve",
    "13": "thirteen",
}


def rename_files_and_directories(root_dir):
    # Rename directories
    for old_dir in os.listdir(root_dir):
        if old_dir in number_to_word:
            new_dir = number_to_word[old_dir]
            old_path = os.path.join(root_dir, old_dir)
            new_path = os.path.join(root_dir, new_dir)
            os.rename(old_path, new_path)
            print(f"Renamed directory: {old_dir} -> {new_dir}")

    # Rename files within directories
    for dir_name, _, files in os.walk(root_dir):
        for file_name in files:
            if file_name.endswith(".JPG") or file_name.endswith(".jpg"):
                # Extract the number from the filename
                number_part = file_name.split(".")[0]
                if number_part in number_to_word:
                    new_file_name = f"{number_to_word[number_part]}.JPG"
                    old_file_path = os.path.join(dir_name, file_name)
                    new_file_path = os.path.join(dir_name, new_file_name)
                    os.rename(old_file_path, new_file_path)
                    print(f"Renamed file: {file_name} -> {new_file_name}")


def rename_JPG_to_jpg(root_dir):
    for dir_name, _, files in os.walk(root_dir):
        for file_name in files:
            if file_name.endswith(".JPG"):
                prefix = file_name.split(".")[0]
                new_file_name = f"{prefix}.jpg"
                old_file_path = os.path.join(dir_name, file_name)
                new_file_path = os.path.join(dir_name, new_file_name)
                os.rename(old_file_path, new_file_path)
                print(f"Renamed file: {file_name} → {new_file_name}")


# Execute the renaming function
rename_JPG_to_jpg("./core/static/core/img/rooms")
