import os
import re
import time
import html
import datetime
import subprocess
from concurrent.futures import ThreadPoolExecutor
import requests
import pymysql
from lxml import etree
#爬取博文requests+XPath
def get_blogs(topic, cookie):
    url = "https://s.weibo.com/weibo"
    target, max_page = 200,30           # 目标200篇,最大爬取页码30
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://s.weibo.com/",
        "Cookie": cookie,
    }
    posts=[] #存放爬出来的博文字典
    seen = set()#记录已经爬过的博文 only_id(博文唯一 id),用来去重
    for page in range(1, max_page + 1):
        # param参数实现翻页
        resp = requests.get(url, params={"q": "#%s#" % topic, "page": page},headers=headers, timeout=20)
        resp.encoding = "utf-8"
        cards = etree.HTML(resp.text).xpath('//div[@class="card-wrap" and @action-type="feed_list_item"]')
        #不重复爬取,加快速度
        if not cards:
            print("第 %d 页没有博文了,停止翻页" % page)
            break
        before = len(posts)                     # 记一下翻页前的数量,用来判断这页有没有新东西
        for card in cards:
            only_id = card.xpath("./@mid")[0]
            # 博主 id
            blogger_id = card.xpath('.//div[@class="avator"]/a/@href')[0].split("?")[0].rsplit("/", 1)[-1]
            #博文内容
            '''
            直接取 feed_list_content_full 就是完整正文,
            取不到(这篇本来就短)再退回 feed_list_content,去掉「展开全文/收起」按钮。
            '''
            content = "".join(card.xpath(
                '(.//p[@node-type="feed_list_content_full"]'
                ' | .//p[@node-type="feed_list_content"][not(../p[@node-type="feed_list_content_full"])])'
                '//text()[not(ancestor::a[@action-type="fl_fold"])]')).strip()
            # 发布时间
            publish_time = "".join(card.xpath('.//div[@class="from"]/a[1]//text()')).strip()
            # 爬取图片视频 视频地址是 JS 对象文本,XPath 取不出来,用正则
            vs = re.search(r"src:\s*'([^']+)'", "".join(card.xpath(
                './/div[@node-type="feed_list_media_prev"]//a[@class="WB_video_h5"]/@data-str')))
            video = "https:" + vs.group(1).replace("\\/", "/") if vs else ""
            images = ["https:" + u if u.startswith("//") else u for u in
                      card.xpath('.//div[@node-type="feed_list_media_prev"]//img/@src') if "sinaimg" in u]
            # 爬取转发,评论,赞
            # 为 0 时微博显示的是「转发」两个字,爬不到数字算0
            acts = ["".join(card.xpath('.//div[@class="card-act"]//li[%d]//text()' % i)) for i in (1, 2, 3)]
            share, comments, likes = [
                t if (re.search(r"[\d.]+", t)) else 0
                for t in acts
            ]
            if only_id and only_id not in seen:            # 翻页时同一条会重复出现,去重
                seen.add(only_id)
                posts.append({
                    "id": only_id,
                    "blogger_id": blogger_id,
                    "user_name": "".join(card.xpath('.//div[@class="info"]/div[2]/a[@class="name"]//text()')).strip(),
                    "publish_time": publish_time,
                    "content": content,
                    "form": "视频" if video else ("图片" if images else "文字"),
                    "share": share,
                    "comments": comments,
                    "likes": likes,
                    "images": images,
                    "video": video,
                    "post_url": "https://weibo.com/%s/%s" % (blogger_id, only_id),
                })
        print("已收集博文 %d / %d 篇" % (len(posts), target))
        # 一页下来没有新的,说明已经翻到底了,不用再请求
        if len(posts) == before or len(posts) >= target:
            print("翻到底了(共 %d 篇),停止翻页" % len(posts))
            break
        time.sleep(1)                              
    return posts[:target]
#爬一级评论:详情页是空壳 SPA,评论只能走接口,fetch_level=0
def get_comments1(post, cookie):
    api = "https://weibo.com/ajax/statuses/buildComments"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": post["post_url"],
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest",
        "client-version": "v2.47.42",              
    }
    #comments存放一级评论;max_id是接口分页游标
    comments, max_id = [], 0
    for _ in range(3):                             # 每篇最多翻 3 页
        data = requests.get(api, headers=headers, timeout=20, params={
            "is_reload": 1, "id": post["id"], "blogger_id": post["blogger_id"], "is_show_bulletin": 2,
            "is_mix": 0, "count": 20, "fetch_level": 0, "max_id": max_id, "locale": "zh-CN",
        }).json()
        if data.get("ok") != 1:
            break
        # 遍历当前分页返回的评论数据
        for c in data["data"]:
            # 评论将表情换成文字
            txt = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r"\1", c.get("text") or "")
            comments.append({
                "id": c["idstr"],
                "blog_id": post["id"],
                "parent_id": None,                 #上一级评论id
                "level": 1,
                "user_name": c["user"]["screen_name"],
                "content": html.unescape("".join(etree.HTML(txt).xpath('//text()'))).strip(),
                "comment_time": datetime.datetime.strptime(
                    c["created_at"], "%a %b %d %H:%M:%S %z %Y"),
                #IP 属地没有的话用get替换为""
                "ip_location": c.get("source", "").replace("来自", "").strip(),
            })
        if not data.get("max_id") or data["max_id"] == max_id:
            break
        max_id = data["max_id"]
        time.sleep(1)
    return comments
#爬二级评论:同一个接口,fetch_level 换成 1,id 传一级评论的 idstr
def get_comments2(comments, post, cookie):
    api = "https://weibo.com/ajax/statuses/buildComments"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": post["post_url"],
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest",
        "client-version": "v2.47.42",
    }
    replies = []
    for c in comments:
        data = requests.get(api, headers=headers, timeout=20, params={
            "is_reload": 1, "id": c["id"], "is_show_bulletin": 2, "is_mix": 0,
            "count": 20, "fetch_level": 1, "max_id": 0, "locale": "zh-CN",
        }).json()
        if data.get("ok") != 1:
            continue
        for r in data["data"]:
            txt = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r"\1", r.get("text") or "")
            replies.append({
                "id": r["idstr"],
                "blog_id": post["id"],
                "parent_id": c["id"],              # 指向回复的那条一级评论
                "level": 2,
                "user_name": r["user"]["screen_name"],
                "content": html.unescape("".join(etree.HTML(txt).xpath('//text()'))).strip(),
                "comment_time": datetime.datetime.strptime(
                    r["created_at"], "%a %b %d %H:%M:%S %z %Y"),
                "ip_location": r.get("source", "").replace("来自", "").strip(),
            })
    return replies
#建数据库和两张表
def create_db(db):
    # 建库这一步连到 MySQL 服务器,不能指定库名(库还不存在)
    conn = pymysql.connect(host=db["host"], port=db["port"], user=db["user"],password=db["password"], charset="utf8mb4")
    conn.cursor().execute("CREATE DATABASE IF NOT EXISTS %s DEFAULT CHARSET utf8mb4"% db["database"])
    conn.commit()
    conn.close()
    conn = pymysql.connect(charset="utf8mb4", **db)     # utf8mb4 才能存 emoji
    cur = conn.cursor()
    #表1:博文表
    cur.execute("""CREATE TABLE IF NOT EXISTS  weibo_blogs (
        id           VARCHAR(100) PRIMARY KEY,   #博文id
        user_name    VARCHAR(100),              #发布者
        user_id      VARCHAR(100),               #发布者id
        publish_time VARCHAR(100),                  #发布时间
        content      MEDIUMTEXT,                #微博正文(完整)
        form         VARCHAR(10),               #形式:文字/图片/视频
        share      INT,                       #转发数
        comments     INT,                       #评论数
        likes        INT,                       #点赞数
        image_paths  TEXT,                      #图片本地路径,逗号分隔
        video_path   VARCHAR(255),              #视频本地路径(没有则为空)
        post_url     VARCHAR(255)               #博文地址
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    #表2:评论表(一级和二级放在同一张表, parent_id / level 区分)
    cur.execute("""CREATE TABLE IF NOT EXISTS weibo_comment (
        id           VARCHAR(100) PRIMARY KEY,   #评论id
        blog_id      VARCHAR(100),               #属于哪篇博文
        parent_id    VARCHAR(100),               #NULL=一级评论;否则=它回复的一级评论id
        level        TINYINT,                   #1=一级评论 2=二级评论
        user_name    VARCHAR(100),              #评论人
        content      TEXT,                      #评论内容
        comment_time DATETIME,                  #评论时间
        ip_location  VARCHAR(50),               #评论人IP属地,如山西
        INDEX idx_post (blog_id)                #按博文查评论时用得上
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    conn.commit()
    conn.close()
    print("数据库 `%s` 建好了( weibo_blogs / weibo_comment 两张表)" % db["database"])
#存入数据库:下载图片视频,存博文,爬一级/二级评论 ,存评论
def save_db(post, cookie, db):
    #try:多线程里某篇博文出错不会终止程序。
    try:
        folder = os.path.join("weibo-image-video", post["id"])
        os.makedirs(folder, exist_ok=True)
        #图片
        image_paths = []
        for i, u in enumerate(post["images"], 1):
            path = os.path.join(folder, "%d.jpg" % i)
            r = requests.get(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://weibo.com/"},
                             timeout=60)
            with open(path, "wb") as f:
                f.write(r.content)
            image_paths.append(path)
        #视频ffmpeg下载 +压到 480p
        video_path = ""
        if post["video"]:
            video_path = os.path.join(folder, "video.mp4")
            subprocess.run([
                r"D:\application\anaconda3\envs\mypython3.11.4\Library\bin\ffmpeg.exe",
                "-y",
                "-tls_verify", "0",                        # 不加会报 certificate verify failed
                "-headers", "Referer: https://weibo.com/\r\n",   # 视频 CDN 认这个,不加 403
                "-i", post["video"],                       # -headers 必须在 -i 前面
                "-vcodec", "libx264", "-crf", "28",        # H.264,crf 越大压得越狠
                "-vf", "scale=-2:480",                     # 高度压到 480p,宽度按比例自动算
                "-preset", "veryfast",                     # 编码速度优先
                video_path,
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        conn = pymysql.connect(charset="utf8mb4", **db)
        cur = conn.cursor()

        #存博文
        cur.execute("""INSERT IGNORE INTO  weibo_blogs
            (id,user_name,user_id,publish_time,content,form,share,comments,likes,
             image_paths,video_path,post_url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
            post["id"], post["user_name"], post["blogger_id"], post["publish_time"],
            post["content"], post["form"], post["share"], post["comments"],
            post["likes"], ",".join(image_paths), video_path, post["post_url"],
        ))
        #爬评论,一级和二级一起存
        comments = get_comments1(post, cookie)
        replies = get_comments2(comments, post, cookie)
        cur.executemany("""INSERT IGNORE INTO weibo_comment
            (id,blog_id,parent_id,level,user_name,content,comment_time,ip_location)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", [
            (c["id"], c["blog_id"], c["parent_id"], c["level"], c["user_name"],
             c["content"], c["comment_time"], c["ip_location"])
            for c in comments + replies
        ])
        conn.commit()
        conn.close()
        print("博文 %s(%s):图片 %d 张、视频 %d 个、一级评论 %d 条、二级评论 %d 条"
              % (post["id"], post["form"], len(image_paths),
                 1 if video_path else 0, len(comments), len(replies)))
    except Exception as e:
        print("博文 %s 处理失败:%s" % (post["id"], e))
#主函数
if __name__ == "__main__":
    topic = "太原理工大学"         
    cookie = ("ALF=1794214230; "
              "SUB=_2A25HzYwGDeRhGeNM6FcS8C3LwjqIHXVkooHOrDV8PUJbkNANLVinkW1NTj05mx8GmWYYP5wpPnva_w11DhmkxWoD;"
              " SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WW69XsvVqUlvxN9yaOsKCHu5JpX5KzhUgL.Fo-Ee0-0eheN1Kq2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMfeoefe050S0.c; SINAGLOBAL=6418668962074.825.1791625939321; "
              "WBPSESS=y7nadm9Cx5aIkEy5Jvmlney6IiAZKe3bRagYoKS4Dff4UmcQzdqmYIqWdfkMtkKe36d26ej4ABwFTuXzvxn7aA_TadInNaJSYfOvjcEEDWzCg5jCK3BErYEskwlSpVGWfWlvnYQG3HfeBptMXgiHxg==; "
              "ULV=1791899490573:3:3:2:1706586822671.199.1791899490503:1791813181877; "
              "PC_TOKEN=071ec6b4da; XSRF-TOKEN=SBhRG7NygCuaLjpHhtS0zhY1")
    db = {"host": "127.0.0.1", "port": 3306, "user": "root",
          "password": "数据库密码", "database": "weibo"}
    #建数据库和两个表
    create_db(db)
    #爬取博文
    posts = get_blogs(topic, cookie)
    if not posts:
        print("一条都没爬到,Cookie 过期,重新从浏览器 F12 复制一个")
        raise SystemExit
    #多线程处理,每篇博文下媒体爬评论入库
    with ThreadPoolExecutor(4) as pool:
        for p in posts:
            pool.submit(save_db, p, cookie, db)
    print("\n全部完成")
