#!/usr/bin/python

"""fetch-macos.py: Fetches macOS products from Apple's SoftwareUpdate service."""

import logging
import plistlib
import os
import errno
import click
import requests
import sys
import re
import gzip

__author__ = "Foxlet"
__copyright__ = "Copyright 2019, FurCode Project"
__license__ = "GPLv3"
__version__ = "1.4"

logging.basicConfig(format='%(asctime)-15s %(message)s', level=logging.INFO)
logger = logging.getLogger('webactivity')


class ClientMeta:
    # Client used to connect to the Software CDN
    osinstall = {"User-Agent":"osinstallersetupplaind (unknown version) CFNetwork/720.5.7 Darwin/14.5.0 (x86_64)"}
    # Client used to connect to the Software Distribution service
    swupdate = {"User-Agent":"Software%20Update (unknown version) CFNetwork/807.0.1 Darwin/16.0.0 (x86_64)"}


class Filesystem:
    @staticmethod
    def download_file(url, size, path):
        label = url.split('/')[-1]
        filename = os.path.join(path, label)
        # Set to stream mode for large files
        remote = requests.get(url, stream=True, headers=ClientMeta.osinstall)

        with open(filename, 'wb') as f:
            with click.progressbar(remote.iter_content(1024), length=size/1024, label="Fetching {} ...".format(filename)) as stream:
                for data in stream:
                    f.write(data)
        return filename

    @staticmethod
    def check_directory(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    @staticmethod
    def fetch_plist(url):
        logging.info("Network Request: %s", "Fetching {}".format(url))
        plist_raw = requests.get(url, headers=ClientMeta.swupdate)
        plist_raw.raise_for_status()
        plist_data = plist_raw.content
        if url.endswith(".gz"):
            plist_data = gzip.decompress(plist_data)
        return plist_data
    
    @staticmethod
    def parse_plist(catalog_data):
        if sys.version_info > (3, 0):
            root = plistlib.loads(catalog_data)
        else:
            root = plistlib.readPlistFromString(catalog_data)
        return root

class SoftwareService:
    # macOS 10.15 is available in 4 different catalogs from SoftwareScan
    catalogs = {
                "26": {
                    "DeveloperSeed":"https://swscan.apple.com/content/catalogs/others/index-26seed-26-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
                    "PublicSeed":"https://swscan.apple.com/content/catalogs/others/index-26beta-26-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz",
                    "PublicRelease":"https://swscan.apple.com/content/catalogs/others/index-26-15-14-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
                        },
                "13": {
                    "DeveloperSeed":"https://swscan.apple.com/content/catalogs/others/index-13seed-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
                    "PublicSeed":"https://swscan.apple.com/content/catalogs/others/index-13beta-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog.gz",
                    "PublicRelease":"https://swscan.apple.com/content/catalogs/others/index-13-12-10.16-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
                        },
                "10.15": {
                    "CustomerSeed":"https://swscan.apple.com/content/catalogs/others/index-10.15customerseed-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
                    "DeveloperSeed":"https://swscan.apple.com/content/catalogs/others/index-10.15seed-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
                    "PublicSeed":"https://swscan.apple.com/content/catalogs/others/index-10.15beta-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog",
                    "PublicRelease":"https://swscan.apple.com/content/catalogs/others/index-10.15-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
                        },
                "10.14": {
                    "PublicRelease":"https://swscan.apple.com/content/catalogs/others/index-10.14-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
                        },
                "10.13": {
                    "PublicRelease":"https://swscan.apple.com/content/catalogs/others/index-10.13-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog"
                        }
                }

    def __init__(self, version, catalog_id):
        self.version = version
        self.catalog_url = self.catalogs.get(version).get(catalog_id)
        self.catalog_data = ""

    def getcatalog(self):
        self.catalog_data = Filesystem.fetch_plist(self.catalog_url)
        return self.catalog_data

    def getosinstall(self):
        # Load catalogs based on Py3/2 lib
        root = Filesystem.parse_plist(self.catalog_data)

        # Iterate to find valid OSInstall packages
        ospackages = []
        products = root['Products']
        for product in products:
            if products.get(product, {}).get('ExtendedMetaInfo', {}).get('InstallAssistantPackageIdentifiers', {}).get('OSInstall', {}) == 'com.apple.mpkg.OSInstall':
                ospackages.append(product)
                
        # Iterate for a specific legacy version. Newer macOS catalogs use full
        # InstallAssistant products without ServerMetadataURL.
        candidates = []
        if self.version.startswith("10."):
            for product in ospackages:
                meta_url = products.get(product, {}).get('ServerMetadataURL', {})
                if self.version in Filesystem.parse_plist(Filesystem.fetch_plist(meta_url)).get('CFBundleShortVersionString', {}):
                    candidates.append(product)

            if candidates:
                return candidates

        # Newer macOS catalogs list full InstallAssistant products instead of
        # OSInstall products with a standalone BaseSystem.dmg.
        modern_candidates = []
        product_name = {
            "26": "macOSTahoe",
            "13": "macOSVentura",
        }.get(self.version)
        for product, info in products.items():
            package_ids = info.get("ExtendedMetaInfo", {}).get("InstallAssistantPackageIdentifiers", {})
            if product_name and package_ids.get("SharedSupport") != "com.apple.pkg.InstallAssistant.{}".format(product_name):
                continue

            package_urls = [item.get("URL", "") for item in info.get("Packages", [])]
            if not any(url.endswith("InstallAssistant.pkg") for url in package_urls):
                continue

            for dist_url in info.get("Distributions", {}).values():
                dist_data = Filesystem.fetch_plist(dist_url).decode("UTF-8")
                version_match = re.search(r'<key>VERSION</key>\s*<string>([^<]+)</string>', dist_data)
                vers_str_match = re.search(r'versStr="([^"]+)"', dist_data)
                versions = [match for match in (version_match, vers_str_match) if match]
                if any(match.group(1).startswith(self.version) for match in versions):
                    modern_candidates.append((info.get("PostDate"), product))
                    break

        candidates.extend(
            product for _, product in sorted(modern_candidates, reverse=True)
        )
        
        return candidates


class MacOSProduct:
    def __init__(self, catalog, product_id):
        root = Filesystem.parse_plist(catalog)
        products = root['Products']
        self.date = root['IndexDate']
        self.product = products[product_id]

    def fetchpackages(self, path, keyword=None):
        Filesystem.check_directory(path)
        packages = self.product['Packages']
        fetched = 0
        if keyword:
            for item in packages:
                if keyword in item.get("URL", ""):
                    Filesystem.download_file(item.get("URL"), item.get("Size"), path)
                    fetched += 1
            if fetched == 0:
                raise ValueError("Selected product does not contain a {} package.".format(keyword))
        else:
            for item in packages:
                Filesystem.download_file(item.get("URL"), item.get("Size"), path)
                fetched += 1

    def haspackage(self, keyword):
        packages = self.product['Packages']
        return any(keyword in item.get("URL", "") for item in packages)

@click.command()
@click.option('-o', '--output-dir', default="BaseSystem/", help="Target directory for package output.")
@click.option('-v', '--catalog-version', default="10.15", help="Version of catalog.")
@click.option('-c', '--catalog-id', default="PublicRelease", help="Name of catalog.")
@click.option('-p', '--product-id', default="", help="Product ID (as seen in SoftwareUpdate).")
@click.option('-k', '--package-keyword', default="BaseSystem", help="Package URL keyword to download.")
def fetchmacos(output_dir="BaseSystem/", catalog_version="10.15", catalog_id="PublicRelease", product_id="", package_keyword="BaseSystem"):
    # Get the remote catalog data
    remote = SoftwareService(catalog_version, catalog_id)
    catalog = remote.getcatalog()

    # If no product is given, find the latest OSInstall product
    if product_id == "":
        candidates = remote.getosinstall()
        if not candidates:
            print("No macOS installer product could be found for catalog version {}.".format(catalog_version))
            exit(1)
        product_id = candidates[0]

    # Fetch the given Product ID
    try:
        product = MacOSProduct(catalog, product_id)
    except KeyError:
        print("Product ID {} could not be found.".format(product_id))
        exit(1)
        
    logging.info("Selected macOS Product: {}".format(product_id))

    # Download package to disk
    if package_keyword == "BaseSystem" and not product.haspackage("BaseSystem") and product.haspackage("InstallAssistant.pkg"):
        print("Selected product is a modern full InstallAssistant.pkg installer.")
        print("This project expects Apple's older standalone BaseSystem.dmg package,")
        print("which is not present in the selected catalog product.")
        exit(1)

    try:
        product.fetchpackages(output_dir, keyword=package_keyword)
    except ValueError as exception:
        print(exception)
        exit(1)

if __name__ == "__main__":
    fetchmacos()
