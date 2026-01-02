import os

IGNORE_FILE_PATH = "ignore_list.txt"
IGNORE_TITLES_PATH = "ignore_titles.txt"


def load_ignore_list():
    """Loads ignore list from file. Returns a set of domains."""
    if not os.path.exists(IGNORE_FILE_PATH):
        return set()

    with open(IGNORE_FILE_PATH, "r") as f:
        lines = f.readlines()

    return {line.strip() for line in lines if line.strip()}


def save_ignore_list(ignore_set):
    """Saves ignore list to file."""
    with open(IGNORE_FILE_PATH, "w") as f:
        for domain in sorted(ignore_set):
            f.write(f"{domain}\n")


def add_domain(domain):
    """Adds a domain to the ignore list."""
    current = load_ignore_list()
    current.add(domain)
    save_ignore_list(current)


def remove_domain(domain):
    """Removes a domain from the ignore list."""
    current = load_ignore_list()
    if domain in current:
        current.remove(domain)
        save_ignore_list(current)


def load_ignore_titles():
    """Loads ignore titles from file. Returns a list of keywords."""
    if not os.path.exists(IGNORE_TITLES_PATH):
        return []

    with open(IGNORE_TITLES_PATH, "r") as f:
        lines = f.readlines()

    return [line.strip() for line in lines if line.strip()]


def save_ignore_titles(titles_list):
    """Saves ignore titles to file."""
    with open(IGNORE_TITLES_PATH, "w") as f:
        for title in sorted(titles_list):
            f.write(f"{title}\n")


def add_ignore_title(title):
    """Adds a title keyword to the ignore list."""
    current = set(load_ignore_titles())
    current.add(title)
    save_ignore_titles(list(current))


def remove_ignore_title(title):
    """Removes a title keyword from the ignore list."""
    current = set(load_ignore_titles())
    if title in current:
        current.remove(title)
        save_ignore_titles(list(current))
