from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
from lxml import etree
from concurrent.futures import ThreadPoolExecutor
import csv
import time
import random
import pymysql
#获取每个电影链接
def get_movie_url(url,child_urls):
    headers1 = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    #拿到页面源代码
    resp=requests.get(url,headers=headers1)
    resp.encoding = "utf-8"
    html=etree.HTML(resp.text)
    # 获得电影子链接(列表)（线程池）
    url_lst=html.xpath('/html/body/div[3]/div[1]/div/div[1]/ol[1]/li//div[@class="hd"]/a/@href')
    #遍历列表单个提取
    for i in url_lst:
        child_urls.append(i)
#获取电影详情
def get_movie_info(child_urls,movie_info_list):
    for child_url in child_urls:
        web.get(child_url)
        time.sleep(random.uniform(4,6)) # 随机4~6秒
        # 源代码
        elements = web.page_source
        child_html = etree.HTML(elements)
        #获取详细信息
#xpath提取
        number = child_html.xpath('//*[@id="content"]//div[@class="top250"]/span[@class="top250-no"]/text()')
        name = child_html.xpath('//*[@id="content"]/h1/span[@property="v:itemreviewed"]/text()')
        year = child_html.xpath('//*[@id="content"]/h1/span[@class="year"]/text()')
        director = child_html.xpath('//*[@id="info"]//span[@class="pl" and contains(text(), "导演")]'
                                    '/following-sibling::span[@class="attrs"]/a[@rel="v:directedBy"]/text()')
        writer = child_html.xpath('//*[@id="info"]//span[@class="pl" and contains(text(), "编剧")]'
                                  '/following-sibling::span[@class="attrs"]/a/text()')
        actors = child_html.xpath('//*[@id="info"]//span/a[@rel="v:starring"]/text()')
        genre = child_html.xpath('//*[@id="info"]//span[@property="v:genre"]/text()')
        country = child_html.xpath('//*[@id="info"]/span[@class="pl" and contains(text(), "制片国家/地区")]'
                                   '/following-sibling::text()[1]')
        language = child_html.xpath('//*[@id="info"]/span[@class="pl" and contains(text(), "语言")]'
                                    '/following-sibling::text()[1]')
        release_date = child_html.xpath('//*[@id="info"]//span[@property="v:initialReleaseDate"]/text()')
        runtime = (child_html.xpath('//*[@id="info"]//span[@class="pl" and contains(text(), "片长")]'
                                    '/following-sibling::span[@property="v:runtime"]/text()')
                   + child_html.xpath('//*[@id="info"]//span[@class="pl" and contains(text(), "片长")]'
                                      '/following-sibling::span[@property="v:runtime"]/following-sibling::text()[1]'))
        aka = child_html.xpath('//*[@id="info"]/span[@class="pl" and contains(text(), "又名")]/following-sibling::text()[1]')
        rating = child_html.xpath('//*[@id="interest_sectl"]//strong[@class="ll rating_num" and @property="v:average"]/text()')
        rating_count = child_html.xpath('//*[@id="interest_sectl"]//a[@class="rating_people"]/span[@property="v:votes"]/text()')
        star5 = child_html.xpath('//*[@id="interest_sectl"]//div[@class="ratings-on-weight"]'
                                 '//div[@class="item"][span[contains(@class, "stars5")]]/span[@class="rating_per"]/text()')
        star4 = child_html.xpath('//*[@id="interest_sectl"]//div[@class="ratings-on-weight"]'
                                 '//div[@class="item"][span[contains(@class, "stars4")]]/span[@class="rating_per"]/text()')
        star3 = child_html.xpath('//*[@id="interest_sectl"]//div[@class="ratings-on-weight"]'
                                 '//div[@class="item"][span[contains(@class, "stars3")]]/span[@class="rating_per"]/text()')
        star2 = child_html.xpath('//*[@id="interest_sectl"]//div[@class="ratings-on-weight"]'
                                 '//div[@class="item"][span[contains(@class, "stars2")]]/span[@class="rating_per"]/text()')
        star1 = child_html.xpath('//*[@id="interest_sectl"]//div[@class="ratings-on-weight"]'
                                 '//div[@class="item"][span[contains(@class, "stars1")]]/span[@class="rating_per"]/text()')
        summary0 = child_html.xpath('//*[@id="link-report-intra"]//span[@property="v:summary"]//text()')
        summary = [l.replace('\n', '').replace('\u3000', '').strip() for l in summary0 if l.strip()]
        '''
#bs4提取
        page = BeautifulSoup(elements, 'html.parser')
        number = [t.get_text(strip=True) for t in page.find_all("span", class_="top250-no")] or ['无数据']
        name = [t.get_text(strip=True) for t in page.find_all("span", property="v:itemreviewed")] or ['无数据']
        year = [t.get_text(strip=True) for t in page.find_all("span", class_="year")] or ['无数据']
        director = [t.get_text(strip=True) for t in page.find_all("a", rel="v:directedBy")] or ['无数据']
        #编剧
        pl = page.find("span", class_="pl", string=re.compile("编剧"))
        atts = pl.find_next_sibling("span", class_="attrs") if pl else None
        writer = [a.get_text(strip=True) for a in atts.find_all("a")] if atts else ['无数据']
        actors = [t.get_text(strip=True) for t in page.find_all("a", rel="v:starring")] or ['无数据']
        genre = [t.get_text(strip=True) for t in page.find_all("span", property="v:genre")] or ['无数据']
        #详情区
        info = page.select_one("div#info")
        #制片国家/地区
        pl = info.find("span", class_="pl", string=re.compile("制片国家/地区")) if info else None
        country = [pl.next_sibling.strip()] if pl and isinstance(pl.next_sibling, str) 
        and pl.next_sibling.strip() else ['无数据']
        #语言
        pl = info.find("span", class_="pl", string=re.compile("语言")) if info else None
        language = [pl.next_sibling.strip()] if pl and isinstance(pl.next_sibling, str) 
        and pl.next_sibling.strip() else ['无数据']
        #又名
        pl = info.find("span", class_="pl", string=re.compile("又名")) if info else None
        aka = [pl.next_sibling.strip()] if pl and isinstance(pl.next_sibling, str) and pl.next_sibling.strip() else ['无数据']
        release_date = [t.get_text(strip=True) for t in page.find_all("span", property="v:initialReleaseDate")] or ['无数据']
        runtime = [t.get_text(strip=True) for t in page.find_all("span", property="v:runtime")] or ['无数据']
        rating = [t.get_text(strip=True) for t in page.find_all("strong", class_="ll rating_num")] or ['无数据']
        rating_count = [t.get_text(strip=True) for t in page.find_all("span", property="v:votes")] or ['无数据']
        #星级占比
        stars = [t.get_text(strip=True) for t in page.find_all("span", class_="rating_per")]
        star5, star4, star3, star2, star1 = [stars[i:i+1] or ['无数据'] for i in range(5)]
        #剧情简介
        summary_tag = page.select_one("#link-report-intra span[property='v:summary']")
        summary0 = [t.replace('\n', '').replace('　', '').strip() for t in summary_tag.find_all(string=True)]
         if summary_tag else []
        summary = [s for s in summary0 if s] or ['无数据']

#正则提取
        obj = re.compile(r'<span class="top250-no">(?P<number>.*?)</span>', re.S)
        number = [i.group("number") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span property="v:itemreviewed">(?P<name>.*?)</span>', re.S)
        name = [i.group("name") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span class="year">(?P<year>.*?)</span>', re.S)
        year = [i.group("year") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<a href="[^"]*" rel="v:directedBy">(?P<director>.*?)</a>', re.S)
        director = [i.group("director") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'\u7f16\u5267</span>: <span class=["\']attrs["\']>(?P<writer>.*?)</span>', re.S)
        writer0 = obj.search(elements)
        writer = re.findall(r'>([^<>]+)</a>', writer0.group("writer")) if writer0 else []
        writer = writer or ['无数据']
        obj = re.compile(r'<a href="[^"]*" rel="v:starring">(?P<actor>.*?)</a>', re.S)
        actors = [i.group("actor") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span property="v:genre">(?P<genre>.*?)</span>', re.S)
        genre = [i.group("genre") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'\u5236\u7247\u56fd\u5bb6/\u5730\u533a:</span>(?P<country>.*?)<br', re.S)
        country = [i.group("country") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'\u8bed\u8a00:</span>(?P<language>.*?)<br', re.S)
        language = [i.group("language") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span property="v:initialReleaseDate"[^>]*>(?P<release_date>.*?)</span>', re.S)
        release_date = [i.group("release_date") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span property="v:runtime"[^>]*>(?P<runtime>.*?)</span>', re.S)
        runtime = [re.sub(r'<[^>]+>', '', i.group("runtime")).strip() for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'\u53c8\u540d:</span>(?P<aka>.*?)<br', re.S)
        aka = [i.group("aka") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<strong class="ll rating_num" property="v:average">(?P<rating>.*?)</strong>', re.S)
        rating = [i.group("rating") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span property="v:votes">(?P<count>.*?)</span>', re.S)
        rating_count = [i.group("count") for i in obj.finditer(elements)] or ['无数据']
        obj = re.compile(r'<span class="rating_per">(?P<star>.*?)</span>', re.S)
        stars = [i.group("star") for i in obj.finditer(elements)] or ['无数据']
        star5, star4, star3, star2, star1 = [stars[i:i+1] or ['无数据'] for i in range(5)]
        obj = re.compile(r'<span property="v:summary"[^>]*>(?P<summary>.*?)</span>', re.S)
        summary1 = obj.search(elements)
        summary0 = re.split(r'<[^>]+>', summary1.group("summary")) if summary1 else []
        summary = [l.replace('\n', '').replace('\u3000', '').strip() for l in summary0 if l.strip()] or ['无数据']
'''
        movie_info_list.append([number,name,year,director,writer,actors,genre,country,language,
                                release_date,runtime,aka,rating,rating_count,star5,star4,star3,star2,star1,summary])
        print("该页提取完毕")
    print("提取完毕")
# 保存到CSV函数
def sava_csv(movie_info_list, filename):
    headers = ['排名','剧名','年份','导演','编剧','主演','类型','制片地区','语言','上映日期','片长',
               '别名','评分','评价人数','五星','四星','三星','二星','一星','剧情']
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(movie_info_list)
def save_db(movie_info_list):
    #连接mysql服务，创建数据库[豆瓣电影]
    conn1 = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='数据库密码')
    cursor1 = conn1.cursor()
    cursor1.execute("CREATE DATABASE IF NOT EXISTS `豆瓣电影` DEFAULT CHARACTER SET utf8mb4")
    cursor1.close()
    conn1.close()
    #重新连接到数据库
    conn = pymysql.connect(host='127.0.0.1',port=3306,user='root',password='数据库密码',database='豆瓣电影')
    cursor = conn.cursor()
    # 创建电影表
    create_sql ='''
    create table if not exists movie_top250(
        排名 varchar(50),
        剧名 varchar(300),
        年份 varchar(50),
        导演 text,
        编剧 text,
        主演 text,
        类型 varchar(300),
        制片地区 varchar(300),
        语言 varchar(500),
        上映日期 text,
        片长 text,
        别名 text,
        评分 varchar(50),
        评价人数 varchar(50),
        五星 varchar(50),
        四星 varchar(50),
        三星 varchar(50),
        二星 varchar(50),
        一星 varchar(50),
        剧情 text
    )
'''
    cursor.execute(create_sql)
    # 批量插入sql
    insert_sql ='''
    insert into movie_top250 (排名,剧名,年份,导演,编剧,主演,类型,制片地区,语言,上映日期,
    片长,别名,评分,评价人数,五星,四星,三星,二星,一星,剧情)
    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
'''
    # 列表处理：空列表存入“无数据”，多值列表用“、”拼接成字符串
    movie_info_list = [[('、'.join(v) if v else '无数据') if isinstance(v, list)
                        else v for v in row] for row in movie_info_list]
    # 批量写入
    cursor.executemany(insert_sql, movie_info_list)
    # 提交事务
    conn.commit()
    # 关闭游标、连接
    cursor.close()
    conn.close()
    print("电影数据写入完成")
#主函数
if __name__=="__main__":
    # 子链接列表
    child_urls = []
    #电影详情列表
    movie_info_list = []
    # 线程池抓取电影子链接
    with ThreadPoolExecutor(50) as t:
        for i in range(1, 11):
            j = 25 * (i - 1)
            # 把下载任务提交给线程池
            t.submit(get_movie_url, f"https://movie.douban.com/top250?start={j}&filter=",child_urls)
    print("电影子链接抓取成功")
    #获取电影信息
    # Selenium使用前配置
    options = Options()
    # 1.指定D盘Chrome路径
    options.binary_location = r"D:\software\chrome\App\chrome.exe"
    # 2.基础防卡死参数
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")
    # 3.隐藏黑色的终端框
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # 只显示致命错误
    options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 隐藏日志窗口
    # 4.浏览器可视
    HEADLESS =True
    # 5.屏蔽国外广告域名
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
    web = Chrome(service=service, options=options)
    time.sleep(5)
    get_movie_info(child_urls, movie_info_list)
    #存入csv文件
    sava_csv(movie_info_list, '豆瓣250电影信息.csv')
    #存入数据库
    save_db(movie_info_list)
    print("全部提取完毕")
