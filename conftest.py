from selenium import webdriver
import pytest
import logging
import os
import allure
import glob


def pytest_addoption(parser):
    parser.addoption(
        '--browser_name',
        default='chrome',
        help='Enter name of browser for testing'
    )
    parser.addoption(
        '--browser_name_remote',
        default='chrome',
        choices=['chrome', 'firefox', 'opera'],
        help='Enter name of remote browser for testing'
    )
    parser.addoption(
        '--url',
        default='http://yandex.ru',
        help='Enter url'
    )
    parser.addoption('--executor', default='localhost')
    parser.addoption('--version_remote_browser', default='102.0')
    parser.addoption('--vnc', action='store_true')
    parser.addoption('--headless', default=False, choices=['true', 'false'])


@allure.step('Start driver')
@pytest.fixture(scope='module')
def browser(request):
    option = webdriver.ChromeOptions()
    option.add_argument('user_agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                        ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36')
    browser_name = request.config.getoption('browser_name').lower()
    executor = request.config.getoption('executor')
    browser_name_remote = request.config.getoption('browser_name_remote')
    version_browser = request.config.getoption('version_remote_browser')
    vnc = request.config.getoption('vnc')
    headless = request.config.getoption('headless')
    if headless == 'true'.lower():
        option.add_argument('--headless')

    if not os.path.exists(os.path.dirname(__file__) + '/logs'):
        os.mkdir(os.path.dirname(__file__) + '/logs')

    log_path = os.path.dirname(__file__) + r'/logs'
    logger = logging.getLogger(request.node.name)
    logger.setLevel(logging.DEBUG)
    create_handler = logging.FileHandler(os.path.join(log_path, f'{request.node.module.__name__}.log'))
    create_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s| %(module)s |%(name)s | %(levelname)s | %(message)s')
    create_handler.setFormatter(formatter)
    logger.addHandler(create_handler)

    if browser_name == 'chrome':
        driver = webdriver.Chrome(options=option)
        logger.info(f'Start driver {browser_name}')
    elif browser_name == 'firefox':
        driver = webdriver.Firefox()
        logger.info(f'Start driver {browser_name}')
    elif browser_name == 'remote':
        capabilities = {
            "browserName": browser_name_remote,
            "browserVersion": version_browser,
            "selenoid:options": {
                "enableVNC": vnc,
                "enableVideo": True
            }
        }
        driver = webdriver.Remote(
            command_executor=f'http://{executor}:4444/wd/hub',
            desired_capabilities=capabilities
        )
        logger.info(f'Start driver {browser_name}')
        driver.implicitly_wait(5)
    else:
        logger.error('Driver not started. Wrong browser name')
        raise AssertionError('Driver not started. Wrong browser name. Choose browser: chrome, firefox or remote')
    driver.logger = logger
    driver.maximize_window()
    yield driver
    logger.info(f'Stop driver {browser_name}')
    driver.quit()


@pytest.fixture
def base_url(request):
    return request.config.getoption('--url')


def pytest_sessionstart():
    files = glob.glob('allure-results/*') + glob.glob('logs/*')
    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    browser = item.funcargs["browser"]
    if rep.when == 'call' and (rep.failed or is_attachment_needed_by_test_name(rep.head_line)):
        allure.attach(
            body=browser.page_source,
            name=rep.head_line + '.html',
            attachment_type=allure.attachment_type.HTML
        )
        allure.attach(
            body=browser.get_screenshot_as_png(),
            name=rep.head_line + '.png',
            attachment_type=allure.attachment_type.PNG
        )


def is_attachment_needed_by_test_name(name):
    return name == 'test_first_category_images_opened_after_click' \
           or name == 'test_image_changed' \
           or name == 'test_image_returned'
