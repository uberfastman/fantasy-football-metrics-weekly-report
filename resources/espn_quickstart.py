import json
from pathlib import Path

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utilities.logger import get_logger

logger = get_logger(__file__)


def extract_espn_session_cookies(web_driver: Chrome):
    if web_driver.get_cookie("SWID") and web_driver.get_cookie("espn_s2"):
        return (
            web_driver.get_cookie("SWID")["value"],
            web_driver.get_cookie("espn_s2")["value"]
        )
    else:
        return None


def main():
    auth_file_path = Path(__file__).parent.parent / "auth" / "espn" / "private.json"
    with open(auth_file_path, "r") as auth_file:
        auth_json = json.load(auth_file)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument(f"--user-data-dir={auth_json.get('chrome_user_data_dir')}")
    options.add_argument(f"--profile-directory={auth_json.get('chrome_user_profile')}")
    driver = Chrome(options=options)
    driver.implicitly_wait(0.5)

    driver.get("https://www.espn.com/fantasy/football/")

    actions = ActionChains(driver)

    try:
        profile_menu = driver.find_element(by=By.ID, value="global-user-trigger")

        # hover over profile menu
        actions.move_to_element(profile_menu).perform()

        # select account management menu
        account_management = driver.find_element(by=By.CLASS_NAME, value="account-management")

        for item in account_management.find_elements(by=By.CSS_SELECTOR, value="a"):
            # click login link from account management
            if item.get_attribute("tref") == "/members/v3_1/login":
                item.click()

        # wait for the modal iframe to appear
        block = WebDriverWait(driver, 2)
        block.until(EC.visibility_of_element_located((By.ID, "oneid-wrapper")))

        # switch driver to modal iframe
        driver.switch_to.frame("oneid-iframe")

        # switch modal form to accept both username and password at once
        username_login = driver.find_element(by=By.ID, value="LaunchLogin")
        for link in username_login.find_elements(by=By.CSS_SELECTOR, value="a"):
            link.click()

        # fill the username and password fields
        driver.find_element(by=By.ID, value="InputLoginValue").send_keys(auth_json.get("username"))
        driver.find_element(by=By.ID, value="InputPassword").send_keys(auth_json.get("password"))

        # submit the login form
        driver.find_element(by=By.ID, value="BtnSubmit").click()

        # switch back to the main page
        driver.switch_to.default_content()

    except (TimeoutException, NoSuchElementException):
        logger.info(f"Already logged in to Chrome with user profile \"{auth_json.get('chrome_user_profile')}\".")

    # retrieve and display session cookies needed for ESPN FF API authentication and extract their values
    swid_cookie, espn_s2_cookie = WebDriverWait(driver, timeout=60).until(lambda d: extract_espn_session_cookies(d))
    logger.info(f"\"SWID\" session cookie: {swid_cookie}")
    logger.info(f"\"espn_s2\" session cookie: {espn_s2_cookie}")

    driver.quit()


if __name__ == "__main__":
    main()
