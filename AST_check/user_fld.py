def check_folder(root):
    files_lst = list()
    for root, dirs, files in os.walk(root):
        for ignored in ignore_paths:
            if ignored in root:
                break

        for filename in files:
            if not set(filename) <= set(legal_chars):
                files_lst.append(filename)
    return files_lst
