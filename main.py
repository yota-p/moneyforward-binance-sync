import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
from logging import getLogger, DEBUG, FileHandler, StreamHandler, Formatter
import datetime
import time
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from get_balance import get_balance_binance_JPY


logger = getLogger('log')
logger.setLevel(DEBUG)
formatter = Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# for file
file_handler = FileHandler('./moneyforward-binance-sync.log')
file_handler.setLevel(DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# for stream
stream_handler = StreamHandler()
stream_handler.setLevel(DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def notify_slack(msg, file_path=None):
    # read token from file
    with open('./secrets/slackauth.json', 'r') as f:
        slackauth = json.load(f)
        token = slackauth['token']
        channel_id = slackauth['channel_id']

    client = WebClient(token=token)

    try:
        if file_path is None:
            # Call the chat.postMessage method using the WebClient
            result = client.chat_postMessage(
                channel=channel_id,
                text=msg
            )
        else:
            # Call the files.upload method using the WebClient
            # Uploading files requires the `files:write` scope
            result = client.files_upload(
                channels=channel_id,
                initial_comment=msg,
                file=file_path,
            )
        logger.info(result)

    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")


def create_screenshot(driver, prefix):
    page_width = driver.execute_script('return document.body.scrollWidth')
    page_height = driver.execute_script('return document.body.scrollHeight')
    driver.set_window_size(page_width, page_height)

    now = datetime.datetime.now()
    currenttime = now.strftime('%Y%m%d_%H%M%S')
    filepath = f"./screenshot/{prefix}_{currenttime}.png"

    driver.save_screenshot(filepath)

    # wait for screenshot file to be created
    start = time.time()
    while time.time() - start <= 30:
        if os.path.exists(filepath):
            break
            time.sleep(1)
        else:
            raise Exception('Failed to create screenshot')

    return filepath


def update_balance(driver, account_id='', asset_id='', balance=0):
    '''
    :params:
    account_id: Hash given for each accounts. Check URL on MoneyForward
    asset_id: Hash given for each assets in the account. Check URL of '変更' on MoneyForward
    '''
    try:
        logger.info(f'Updating balance for: account_id={account_id}, asset_id={asset_id}')
        URL = f'https://moneyforward.com/accounts/show_manual/{account_id}'
        driver.get(URL)
        WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)
        time.sleep(10)

        form = driver.find_element_by_id('portfolio_det_depo')
        form.find_element_by_class_name('btn-asset-action').click()
        form.find_element_by_id('user_asset_det_value').clear()
        form.find_element_by_id('user_asset_det_value').send_keys(balance)

        submitbutton = form.find_element_by_xpath(f'//*[@id="new_user_asset_det_{asset_id}"]/div[7]/div/input')
        submitbutton.click()

    except Exception:
        filepath = create_screenshot(driver, 'error')
        notify_slack('Failed to update. \n' + traceback.format_exc(), filepath)

    finally:
        driver.quit()


def fetch_balance(driver, args=None):
    driver.get("https://moneyforward.com/")
    WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)

    for e in driver.find_elements_by_css_selector(".refresh.btn.icon-refresh"):
        if e.text == "一括更新":
            e.click()
            logger.debug("reload clicked")
    return


def login(user, password):
    URL = "https://moneyforward.com/sign_in"

    try:
        options = Options()
        # options.add_argument('--headless')
        driver = webdriver.Chrome("./chromedriver", options=options)

        # driver.implicitly_wait(10)
        driver.get(URL)
        WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)

        # login
        elem = driver.find_element_by_css_selector(".ssoText")
        elem.click()
        elem = driver.find_element_by_css_selector(".inputItem")
        elem.clear()
        elem.send_keys(user)
        logger.debug("email sent")
        elem = driver.find_element_by_css_selector(".submitBtn.homeDomain")
        elem.click()
        elem = driver.find_element_by_css_selector(".inputItem")
        logger.debug("password sent")
        elem.clear()
        elem.send_keys(password)
        elem = driver.find_element_by_css_selector(".submitBtn.homeDomain")
        elem.click()
        logger.debug("login successful")
    except Exception:
        filepath = create_screenshot(driver, 'error')
        notify_slack('Failed to book. \n' + traceback.format_exc(), filepath)
    return driver


if __name__ == '__main__':
    with open('./secrets/config.json', 'r') as f:
        config = json.load(f)
    balance = get_balance_binance_JPY(config['Binance']['API_KEY'], config['Binance']['API_SECRET'])
    driver = login(config['MoneyForward']['email'], config['MoneyForward']['password'])
    update_balance(driver, config['MoneyForward']['account_id'], config['MoneyForward']['asset_id'], balance)
