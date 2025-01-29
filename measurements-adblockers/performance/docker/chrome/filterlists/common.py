import pathlib
import time
from selenium.webdriver.common.by import By


extensions_mid_filterlists = {
    "adguard": [
        "AdGuard Base",
        "AdGuard Tracking Protection",
        "AdGuard Social Media",
        "AdGuard Annoyances",
        "AdGuard URL Tracking",
        "AdGuard Russian",
        "AdGuard Japanese",
        "NoCoin Filter List",
        "Online Malicious URL Blocklist",
        "AdGuard Chinese",
        "AdGuard Mobile Ads",
        "Legitimate URL Shortener",
        "AdGuard Cookie Notices",
        "AdGuard Other Annoyances",
        "AdGuard Spanish/Portuguese",
        "AdGuard German",
        "AdGuard Mobile App Banners",
        "AdGuard Widgets",
        "official polish filters for adblock, ublock origin & adguard",
        "AdGuard French",
        "EasyList Italy",
        "Adblock Warning Removal List",
        "AdGuard Turkish",
        "Filter unblocking search ads and self-promotion",
        "AdGuard Dutch",
        "AdBlockID",
    ],
    "ublock": [
        "ublock-filters",
        "ublock-unbreak",
        "ublock-privacy",
        "ublock-badware",
        "easylist",
        "easyprivacy",
        "urlhaus-1",
        "plowe-0",
        "ublock-quick-fixes",
        "ublock-annoyances",
        "adguard-mobile",
        "fanboy-cookiemonster",
        "adguard-generic",
        "adguard-spyware-url",
        "adguard-social",
        "adguard-annoyances",
        "easylist-annoyances",
        "adguard-spyware",
        "curben-phishing",
        "block-lan",
        "fanboy-social",
        "fanboy-thirdparty_social",
        "DEU-0",
        "spa-1",
        "adguard-cookies",
        "RUS-0",
        "FRA-0",
        "adguard-popup-overlays",
    ],
}


def _get_extension_id(profile_path):

    if not (pathlib.Path(profile_path) / "Local Extension Settings/").exists():
        return None

    # if it contains at least one folder
    for manifest_fp in (
        pathlib.Path(profile_path) / "Local Extension Settings/"
    ).iterdir():
        return manifest_fp.name

    return None


def wait_until_extension(profile_path, timeout=60, period=0.25, min_time=0):
    """Wait until an extension is found in the profile path"""
    start_time = time.time()
    mustend = time.time() + timeout
    while time.time() < mustend:
        extension_id = _get_extension_id(profile_path)
        if extension_id is not None:
            if time.time() - start_time < min_time:
                time.sleep(min_time + start_time - time.time())
            return extension_id
        time.sleep(period)
    raise Exception("Extension not found")


def get_extension_id(driver):
    """Get the extension id of the extension with the given name"""

    driver.get("chrome://version")
    wait_until_loaded(driver, 10)

    profile_path = driver.find_element(By.XPATH, '//*[@id="profile_path"]')
    profile_path = profile_path.text

    extension_id = wait_until_extension(profile_path)

    return extension_id


def is_loaded(webdriver):
    """Check if the page is loaded"""
    return webdriver.execute_script("return document.readyState") == "complete"


def wait_until_loaded(webdriver, timeout=60, period=0.25, min_time=0):
    """Wait until the page is loaded"""
    start_time = time.time()
    mustend = time.time() + timeout
    while time.time() < mustend:
        if is_loaded(webdriver):
            if time.time() - start_time < min_time:
                time.sleep(min_time + start_time - time.time())
            return True
        time.sleep(period)
    return False
