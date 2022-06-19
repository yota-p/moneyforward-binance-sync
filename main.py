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
file_handler = FileHandler('./main.log')
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
        enable = slackauth['enable']
        token = slackauth['token']
        channel_id = slackauth['channel_id']

    if enable is False:
        return

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


def update_balance(driver, account_id='', balance=0):
    '''
    :params:
    account_id: Hash given for each accounts. Check URL on MoneyForward
    '''
    logger.info(f'Updating balance for: account_id={account_id}, balance={balance}')
    # open page
    URL = f'https://moneyforward.com/accounts/show_manual/{account_id}'
    driver.get(URL)
    WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)
    time.sleep(5)

    # open 残高修正
    form = driver.find_element_by_xpath('/html/body/div[1]/div[2]/div/div[1]/div/div/section/h1[2]/a')
    form.click()
    time.sleep(3)
    # write 修正後の残高
    form.find_element_by_xpath('/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[2]/div/div/input').send_keys(balance)
    # uncheck 不明金として記帳
    # form.find_element_by_xpath('/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[3]/div/label/input[2]').click()

    submitbutton = form.find_element_by_xpath('/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[5]/div/input')
    submitbutton.click()

    logger.info('Successfully updated balance.')


def fetch_balance(driver):
    driver.get("https://moneyforward.com/")
    WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)

    for e in driver.find_elements_by_css_selector(".refresh.btn.icon-refresh"):
        if e.text == "一括更新":
            e.click()
            logger.info("Reload clicked")
    return


def login(driver, user, password):
    logger.info('Login to MoneyForward.')

    URL = "https://moneyforward.com/sign_in"

    # driver.implicitly_wait(10)
    driver.get(URL)
    WebDriverWait(driver, 60).until(EC.presence_of_all_elements_located)
    time.sleep(3)

    # login
    elem = driver.find_element_by_css_selector(".ssoText")
    elem.click()
    elem = driver.find_element_by_css_selector(".inputItem")
    elem.clear()
    elem.send_keys(user)
    elem = driver.find_element_by_css_selector(".submitBtn.homeDomain")
    elem.click()
    elem = driver.find_element_by_css_selector(".inputItem")
    elem.clear()
    elem.send_keys(password)
    elem = driver.find_element_by_css_selector(".submitBtn.homeDomain")
    elem.click()
    logger.info("Login successful")

    return driver


if __name__ == '__main__':
    # get balance
    with open('./secrets/config.json', 'r') as f:
        config = json.load(f)
    balance = get_balance_binance_JPY(config['Binance']['API_KEY'], config['Binance']['API_SECRET'])

    # create driver
    options = Options()
    # set headless to True, if you don't need to display browser
    if config['headless']:
        options.add_argument('--headless')
    # When using headless option, some websites detect this as a bot and return blank page.
    # Thus we specify user_agent to make headless undetectable
    # Ref: https://intoli.com/blog/making-chrome-headless-undetectable/
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    driver = webdriver.Chrome("./chromedriver", options=options)

    # login & update
    try:
        driver = login(driver, config['MoneyForward']['email'], config['MoneyForward']['password'])
        fetch_balance(driver)
        update_balance(driver, config['MoneyForward']['account_id'], balance)
    except Exception:
        filepath = create_screenshot(driver, 'error')
        notify_slack('Failed to sync. \n' + traceback.format_exc(), filepath)
        logger.error('Failed to sync. \n' + traceback.format_exc())
    finally:
        driver.quit()
