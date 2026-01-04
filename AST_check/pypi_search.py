import sys
import datetime
import requests
from bs4 import BeautifulSoup
from behoof import load_json, save_json


def pypi_search(package_name):

    url = f"https://pypi.org/simple/{package_name}/"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a", href=True)
    packages = []
    for link in links:
        package_info = {
            "filename": link.get_text(strip=True),
            "url": link["href"],
            "requires_python": link.get("data-requires-python"),
            "dist_info_metadata_sha256": link.get("data-dist-info-metadata"),
            "core_metadata_sha256": link.get("data-core-metadata"),
            "check_date": datetime.datetime.now().isoformat(),
        }
        packages.append(package_info)
    return packages


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python pypi_search.py <имя_пакета>")
        sys.exit(1)
    package_name = sys.argv[1]
    pypi_lst = pypi_search(package_name)

    package_dct = load_json("data", "package.json")
    package_dct[package_name] = pypi_lst
    package_dct = save_json("data", "package.json", package_dct)
