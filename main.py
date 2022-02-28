import os
import pickle
import re
import time
from time import sleep

import requests
from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

COOKIES_PATH = '../cook.pkl'
URL_TO_SCRAPE = 'your-url-here'
TITLE_XPATH = '//a[starts-with(@class, "sidebar-lesson__title")]'
SECTION_XPATH = '//a[starts-with(@class, "section-link")]'
PAGE_XPATH = '//a[starts-with(@class, "page-item")]'
CONTENT_XPATH = '//div[starts-with(@class, "step__viewer")]'

IMG_PATTERN = re.compile(r'<\s*img [^>]*src="([^"]+)')


class CourseScraper:
    def __init__(self, cookies: str = COOKIES_PATH, url: str = URL_TO_SCRAPE):
        """
        Initialize class instance
        :param cookies: path to a pickle containing cookie dicts (as given by selenium)
        :param url: url string
        """
        self._cookies = cookies
        self.url = url
        self._prepare_driver()
        self._load_cookies()

    def _prepare_driver(self):
        """
        Method to load Chrome Driver
        """
        driver_manager = ChromeDriverManager().install()
        self.driver = webdriver.Chrome(driver_manager)

    def _load_cookies(self):
        """
        Method to read cookies and load them into driver
        """
        with open(self._cookies, 'rb') as handle:
            cookies = pickle.load(handle)
        self.driver.get(self.url)
        for cook in cookies:
            try:
                self.driver.add_cookie(cook)
            except InvalidCookieDomainException:
                pass

    def get_titles(self):
        """
        Method to read high-level titles from webpage
        """
        self.driver.get(self.url)
        time.sleep(5)
        titles = self.driver.find_elements(by=By.XPATH, value=TITLE_XPATH)
        num_titles = len(titles)
        print(num_titles)

        for i in range(num_titles):
            self.driver.get(self.url)
            time.sleep(5)
            titles = self.driver.find_elements(by=By.XPATH, value=TITLE_XPATH)
            curr_title = titles[i]
            title_name = curr_title.text
            title_name = re.sub(r'[^a-zA-Zа-яА-Я0-9]+\s*', "_", title_name).lower()
            title_name = title_name.split('_')
            title_name = '_'.join([title_name[0]] + title_name[2:])
            os.mkdir(title_name)
            curr_title.click()
            time.sleep(1)
            self.get_sections(title_name)

    def get_sections(self, title_name: str):
        """
        Method to read middle-level titles. Needs higher-level title string
        to pass for saving
        :param title_name: name of higher-level title
        """
        sections = self.driver.find_elements(by=By.XPATH, value=SECTION_XPATH)
        num_sections = len(sections)

        os.mkdir(os.path.join(title_name, sections[0].text))
        self.save_page(title_name, sections[0].text, 0)

        for j in range(1, num_sections):
            sections = self.driver.find_elements(by=By.XPATH, value=SECTION_XPATH)
            curr_section = sections[j]
            section_name = curr_section.text
            os.mkdir(os.path.join(title_name, section_name))
            curr_section.click()
            self.get_pages(title_name, section_name)

    def get_pages(self, title_name, section_name) -> None:
        """
        Method to load a list of pages from the website.
        :param title_name: string with the name of the title
        :param section_name: string with the name of the sub-section
        """
        pages = self.driver.find_elements(by=By.XPATH, value=PAGE_XPATH)
        num_pages = len(pages)

        if num_pages > 0:
            for k in range(num_pages):
                pages = self.driver.find_elements(by=By.XPATH, value=PAGE_XPATH)
                pages[k].click()
                self.save_page(title_name, section_name, k)
        else:
            self.save_page(title_name, section_name, 0)

    def save_page(self, title_name, section_name, page_number) -> None:
        """
        Method to save the pages. Loads the page, extracts its source code and writes it to a file.
        :param title_name: title string
        :param section_name: subsection name string
        :param page_number: page number
        """
        sleep(0.5)
        ele = self.driver.find_element(by=By.XPATH, value=CONTENT_XPATH)
        path_to_save = os.path.join(title_name, section_name)
        source_code = ele.get_attribute('innerHTML')
        self._get_images(source_code, path_to_save)
        source_code = re.sub(IMG_PATTERN, lambda x: self._fix_str(x.group(0)), source_code)
        with open(os.path.join(path_to_save, f'page_{page_number}.html'), 'w') as f:
            f.write(source_code)

    @staticmethod
    def _fix_str(in_string: str) -> str:
        """
        Auxiliary method to substitute links to local filenames in HTML
        :param in_string: html code
        :return: html code with fixed links
        """
        fixed_string = (
            in_string.split('src=')[0] + 'src="'
            + '_'.join(in_string.split('src=')[-1].split('/')[-2:])
        )
        return fixed_string

    @staticmethod
    def _get_images(html: str, path: str) -> None:
        """
        Auxiliary method to save images from the extracted html code.
        :param html: raw html code as a string
        :param path: path to save data
        """
        images = IMG_PATTERN.findall(html)
        for image in images:
            img_data = requests.get(image).content
            file_name = '_'.join(image.split('/')[-2:])
            with open(os.path.join(path, f'{file_name}'), 'wb') as handler:
                handler.write(img_data)


def main():
    scr = CourseScraper()
    scr.get_titles()


if __name__ == '__main__':
    main()
