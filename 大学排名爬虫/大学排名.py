from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import csv
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

#Selenium使用前配置
options = Options()
#1.指定D盘Chrome路径
options.binary_location = r"D:\software\chrome\App\chrome.exe"
#2.基础防卡死参数
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
#3.隐藏黑色的终端框
options.add_argument("--disable-logging")
options.add_argument("--log-level=3")  # 只显示致命错误
options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 隐藏日志窗口
#4.浏览器可视
HEADLESS = False
#5.屏蔽国外广告域名
options.add_argument(
    "--host-resolver-rules="
    "MAP *.google.com ~NOTFOUND,"
    "MAP *.googleapis.com ~NOTFOUND,"
    "MAP *.gstatic.com ~NOTFOUND,"
    "MAP *.googlesyndication.com ~NOTFOUND,"
    "MAP *.doubleclick.net ~NOTFOUND,"
    "MAP *.google-analytics.com ~NOTFOUND,"
    "MAP *.googletagmanager.com ~NOTFOUND")

if HEADLESS:
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")

service = Service(r"D:\application\anaconda3\envs\mypython3.11.4\chromedriver.exe")
# 获取信息函数
def get_info(html, ulist):
    page = BeautifulSoup(html, 'html.parser')
    #拿到表格
    table = page.find("tbody")
    #拿到所有的行数据
    trs = table.find_all("tr")
    # 遍历表格tbody里每一行tr
    for tr in trs:
        tds = tr.find_all('td')
        #排名：td[0]下 div.ranking 的文本
        rank = tds[0].get_text(strip=True)
        #中英文校名：td[1]下所有span
        spans = tds[1].find_all("span")
        #中文
        ch_name = spans[0].get_text(strip=True)
        #英文
        en_name = spans[1].get_text(strip=True)
        #省份
        area = tds[2].get_text(strip=True)
        #评分
        score = tds[4].get_text(strip=True)
        #办学层次
        layer = tds[5].get_text(strip=True)
        # 存入列表
        ulist.append([rank, ch_name, en_name, area, score, layer])

# 保存到CSV函数
def sava_csv(ulist, filename):
    headers = ['排名', '学校名字', '英文名', '省份','评分','办学层次', ]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(ulist)

# 鼠标操作运行函数
def action_run(web, info, by=By.ID,):
    next_page = web.find_element(by=by, value=info)
    next_page.click()

# 主函数
if __name__ == "__main__":
    url = "https://www.shanghairanking.cn/rankings/bcur/2024"
    web =Chrome(service=service, options=options)
    web.get(url)
    time.sleep(2)
    #大学信息列表
    ulist = []
    #获取信息
    for i in range(20):
        html = web.page_source
        get_info(html, ulist)
        action_run(web, info="li[title='下一页']", by=By.CSS_SELECTOR)
    # 关闭浏览器
    web.quit()
    # 保存为CSV文件
    sava_csv(ulist, '大学排名.csv')

