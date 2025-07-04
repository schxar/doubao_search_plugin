from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 自动下载并启动
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://www.baidu.com")
print(driver.title)
driver.quit()