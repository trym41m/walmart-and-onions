from selenium import webdriver
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver import ActionChains
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import os
from random import randint
from random import uniform
import logging
import cv2
from PIL import Image
from io import BytesIO
import numpy as np

url = "https://www.walmart.com/ip/White-Onions-each/51259208"
path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

class GenericPriceScraper(object):
	def __init__(self, url, driver):
		self.url = url
		self.driver = driver
		self.logger = logging.getLogger(__name__)

	@staticmethod
	def gen_user_agent_options():
		options = Options()
		ua = UserAgent()
		user_agent = ua.random
		# hard-code my own user-agent :(
		user_agent = os.environ['USER_AGENT']

		# WARNING - Flakey - Adds proxy
		# 
		# proxy_ip = "184.105.186.70:3128"
		# options.add_argument(f"--proxy-server={proxy_ip}")
		dir(options)
		return options

	def iam_not_a_robot(self, driver):

		"""
		First Method

		These methods come from these geniuses, or grifters ... you decide
		https://stackoverflow.com/questions/68636955/how-to-long-press-press-and-hold-mouse-left-key-using-only-selenium-in-python
		"""

		# element = driver.find_element(By.CSS_SELECTOR, "#px-captcha")
		# action = ActionChains(driver)
		# click = ActionChains(driver)
		# action.click_and_hold(element)
		# action.perform()
		# time.sleep(uniform(15,30))
		# action.release(element)
		# action.perform()
		# time.sleep(uniform(0,1))
		# action.release(element)

		"""
		Second Method
		"""
		
		# element = driver.find_element(By.XPATH, "//div[@id='px-captcha']")
		# print(len(element.text), '- Value found by method text')
		# frame_x = element.location['x']
		# frame_y = element.location['y']
		# print('x: ', frame_x)
		# print('y: ', frame_y)
		# print('size box: ', element.size)
		# print('x max click: ', frame_x + element.size['width'])
		# print('y max click: ', frame_y + element.size['height'])

		# x_move = frame_x + element.size['width']*0.5
		# y_move = frame_y + element.size['height']*0.5
		# action.move_to_element_with_offset(element, x_move, y_move).click_and_hold().perform()
		# time.sleep(10)
		# action.release(element)
		# action.perform()
		# time.sleep(0.2)
		# action.release(element)

		"""
		Third Method
		"""
		
		self.solve_blocked(driver)

	def get_url(self, driver):
		time.sleep(randint(1,5))
		driver.get(self.url)

	def solve_blocked(self, driver, retry=3):
		'''
		Solve blocked
		(Cross-domain iframe cannot get elements temporarily)
		Simulate the mouse press and hold to complete the verification
		'''
		if not retry:
			return False
		element = None
		try:
			element = WebDriverWait(driver,15).until(EC.presence_of_element_located((By.ID,'px-captcha')))
			# Wait for the px-captcha element styles to fully load
			time.sleep(0.5)
		except BaseException as e:
			self.logger.info(f'px-captcha element not found')
			return
		self.logger.info(f'solve blocked:{driver.current_url}, Retry {retry} remaining times')
		template = cv2.imread('captcha.png')
		# Set the minimum number of feature points to match value 10
		MIN_MATCH_COUNT = 8
		if  element:
			self.logger.info(f'start press and hold')
			ActionChains(driver).click_and_hold(element).perform()
			start_time = time.time()
			while 1:
				# timeout
				if time.time() - start_time > 20:
					break
				x, y = element.location['x'], element.location['y']
				width, height = element.size.get('width'), element.size.get('height')
				left = x
				top = y
				right = (x+width)
				bottom = (y+height)
				# full screenshot
				png = driver.get_screenshot_as_png() 
				im = Image.open(BytesIO(png))
				# px-captcha screenshot
				im = im.crop((left, top, right, bottom)) 
				target = cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2BGR)  
				# Initiate SIFT detector
				sift = cv2.SIFT_create()
				# find the keypoints and descriptors with SIFT
				kp1, des1 = sift.detectAndCompute(template,None)
				kp2, des2 = sift.detectAndCompute(target,None)
				# create set FLANN match
				FLANN_INDEX_KDTREE = 0
				index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
				search_params = dict(checks = 50)
				flann = cv2.FlannBasedMatcher(index_params, search_params)
				matches = flann.knnMatch(des1,des2,k=2)
				# store all the good matches as per Lowe's ratio test.
				good = []
				# Discard matches greater than 0.7
				
				for m,n in matches:
					if m.distance < 0.7*n.distance:
						good.append(m)
				self.logger.info( "matches are found - %d/%d" % (len(good),MIN_MATCH_COUNT))
				if len(good)>=MIN_MATCH_COUNT:
					self.logger.info(f'release button')
					ActionChains(driver).release(element).perform()
					return
				time.sleep(0.5)
		time.sleep(1)
		retry -= 1
		self.solve_blocked(retry)

	def find_potential_elements(self, driver):
		# mr2 is hard-coded for now and might not be the class name for all items
		elems = driver.find_elements(By.CLASS_NAME, "mr2")
		text_elements = [e.text for e in elems]
		matched_unit_price = re.findall(r"(\d+\W\d+)", ''.join(text_elements))
		return matched_unit_price

	def delete_all_cookies(self, driver):
		driver.delete_all_cookies()

	def execute_unit_price_scrape_for_location(self, driver):
		self.delete_all_cookies(driver)
		self.get_url(driver)
		time.sleep(randint(1,5))
		self.iam_not_a_robot(driver)
		time.sleep(randint(1,5))
		matched_unit_price = self.find_potential_elements(driver)
		return matched_unit_price

if __name__ == '__main__':

	options = GenericPriceScraper.gen_user_agent_options()

	try:
		os.system("rm -rf /Users/m/.wdm/drivers/chromedriver/mac64/108.0.5359/chromedriver")
	except Exception:
		pass

	cdm_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
	driver = webdriver.Chrome(options=options, service=Service(cdm_path))

	gps = GenericPriceScraper(url, driver)

	unit_price = gps.execute_unit_price_scrape_for_location(driver)

	print(unit_price)
