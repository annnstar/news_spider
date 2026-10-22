# -*- coding: utf-8 -*-
"""
中国新闻网滚动新闻爬虫（练习项目）
------------------------------------
目标：抓取滚动新闻列表（标题 / 分类 / 时间 / 链接），
      进入详情页补齐来源、正文长度、图片，存 CSV，可选写 MySQL、下载图片。

运行：
    python spider.py --limit 5
    python spider.py --max-pages 3 --images
    python spider.py --mysql --password 你的密码

依赖：
    pip install -r requirements.txt
"""

import argparse
import csv
import logging
import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.chinanews.com.cn"
START_URL = BASE_URL + "/scroll-news/news1.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CSV_FIELDS = [
    "article_id", "title", "category", "publish_time", "list_time",
    "source", "content_len", "image_count", "image_url", "image_file", "url",
]


# ---------------------------------------------------------------- 基础工具

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def fetch(session, url, retries=3, timeout=15):
    """请求页面，失败重试 3 次；成功返回 HTML，彻底失败返回 None。"""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            if resp.status_code == 404:
                logging.info("页面不存在（404）：%s", url)
                return None
            logging.warning("HTTP %s %s（第 %d 次）", resp.status_code, url, attempt)
        except requests.exceptions.SSLError as exc:
            logging.error("TLS 握手失败 %s：%s", url, exc)
            return None
        except requests.RequestException as exc:
            logging.warning("请求异常 %s（%s），第 %d 次", url, exc, attempt)
        time.sleep(attempt * 1.5)
    logging.error("放弃该 URL：%s", url)
    return None


def extract_article_id(url):
    """从 /sh/2026/10-22/10718934.shtml 里取出 10718934。"""
    match = re.search(r"/(?:news)?(\d+)\.shtml", url)
    return match.group(1) if match else ""


# ---------------------------------------------------------------- 页面解析

def parse_list_page(html, page_url):
    """解析滚动新闻列表页，返回新闻条目列表。"""
    soup = BeautifulSoup(html, "lxml")
    items = []

    for li in soup.select(".content_list li"):
        link = li.select_one(".dd_bt a")
        if link is None or not link.get("href"):
            continue

        category_tag = li.select_one(".dd_lm a")
        time_tag = li.select_one(".dd_time")
        url = urljoin(page_url, link.get("href"))

        items.append({
            "title": link.get_text(strip=True),
            "category": category_tag.get_text(strip=True) if category_tag else "",
            "list_time": time_tag.get_text(strip=True) if time_tag else "",
            "url": url,
            "article_id": extract_article_id(url),
        })

    return items


def parse_detail_page(html, url):
    """解析新闻详情页：标题、完整时间、来源、正文长度、图片。"""
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.select_one(".content_left_title")
    info_tag = soup.select_one(".content_left_time")
    content_tag = soup.select_one(".left_zw")

    publish_time, source = "", ""
    if info_tag:
        info_text = info_tag.get_text(" ", strip=True)
        time_match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2})", info_text)
        if time_match:
            publish_time = time_match.group(1)
        source_match = re.search(r"来源[：:]\s*(\S+)", info_text)
        if source_match:
            source = source_match.group(1)

    content = content_tag.get_text(" ", strip=True) if content_tag else ""
    images = []
    if content_tag:
        for img in content_tag.select("img"):
            src = img.get("src", "").strip()
            if src:
                images.append(urljoin(url, src))

    return {
        "publish_time": publish_time,
        "source": source,
        "content_len": len(content),
        "image_count": len(images),
        "image_url": images[0] if images else "",
    }


# ---------------------------------------------------------------- 存储

def load_seen(out_dir):
    path = os.path.join(out_dir, "news.csv")
    seen = set()
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("article_id"):
                    seen.add(row["article_id"])
    return seen


def save_csv(rows, out_dir):
    path = os.path.join(out_dir, "news.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logging.info("已写入 CSV：%s（%d 条）", path, len(rows))


def download_images(session, rows, out_dir):
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    ok = fail = 0

    for row in rows:
        url = row.get("image_url")
        if not url:
            continue
        name = (row.get("article_id") or str(ok)) + ".jpg"
        path = os.path.join(img_dir, name)
        if os.path.exists(path):
            ok += 1
            continue
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200 and resp.content:
                with open(path, "wb") as f:
                    f.write(resp.content)
                row["image_file"] = os.path.join("images", name)
                ok += 1
            else:
                fail += 1
                logging.warning("图片下载失败 %s：HTTP %s", url, resp.status_code)
        except requests.RequestException as exc:
            fail += 1
            logging.warning("图片下载异常 %s：%s", url, exc)
        time.sleep(0.2)
    logging.info("图片下载完成：成功 %d，失败 %d", ok, fail)


def save_mysql(rows, cfg):
    try:
        import pymysql
    except ImportError:
        logging.error("未安装 pymysql：pip install pymysql")
        return

    conn = pymysql.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], database=cfg["database"], charset="utf8mb4",
    )
    sql = """
    INSERT INTO news
        (article_id, title, category, publish_time, list_time, source,
         content_len, image_count, image_url, image_file, url)
    VALUES
        (%(article_id)s, %(title)s, %(category)s, %(publish_time)s, %(list_time)s,
         %(source)s, %(content_len)s, %(image_count)s, %(image_url)s,
         %(image_file)s, %(url)s)
    ON DUPLICATE KEY UPDATE
        title=VALUES(title), publish_time=VALUES(publish_time),
        content_len=VALUES(content_len), image_file=VALUES(image_file)
    """
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
        logging.info("已写入 MySQL：%d 条", len(rows))
    finally:
        conn.close()


# ---------------------------------------------------------------- 主流程

def next_page_url(current_url):
    """news1.html -> news2.html -> news3.html ..."""
    match = re.search(r"news(\d+)\.html", current_url)
    if not match:
        return None
    return current_url[:match.start()] + "news" + str(int(match.group(1)) + 1) + ".html"


def crawl(args):
    os.makedirs(args.outdir, exist_ok=True)
    setup_logging(os.path.join(args.outdir, "spider.log"))

    session = requests.Session()
    seen = load_seen(args.outdir)
    rows = []

    url = args.start_url
    page = 1
    while url:
        logging.info("列表页 %d：%s", page, url)
        html = fetch(session, url)
        if html is None:
            break

        items = parse_list_page(html, url)
        logging.info("  本页解析到 %d 条新闻", len(items))
        if not items:
            break

        for item in items:
            if item["article_id"] in seen:
                continue
            detail_html = fetch(session, item["url"])
            if detail_html is None:
                continue

            detail = parse_detail_page(detail_html, item["url"])
            if detail["content_len"] == 0 and detail["image_count"] == 0:
                logging.warning("跳过无正文页面：%s", item["url"])
                continue
            row = {**item, **detail}
            row.setdefault("image_file", "")
            rows.append(row)
            seen.add(item["article_id"])

            logging.info("  [%d] %s", len(rows), row["title"][:40])
            if args.limit and len(rows) >= args.limit:
                break
            time.sleep(args.delay)

        if args.limit and len(rows) >= args.limit:
            break
        if page >= args.max_pages:
            break
        url = next_page_url(url)
        page += 1

    if not rows:
        logging.warning("没有抓到数据，检查网络或页面结构")
        return

    if args.images:
        download_images(session, rows, args.outdir)

    save_csv(rows, args.outdir)

    if args.mysql:
        save_mysql(rows, {
            "host": args.host, "port": args.port, "user": args.user,
            "password": args.password, "database": args.database,
        })

    logging.info("全部完成，共 %d 条", len(rows))


def main():
    parser = argparse.ArgumentParser(description="中国新闻网滚动新闻爬虫（练习）")
    parser.add_argument("--limit", type=int, default=0, help="最多抓多少条，0 表示不限")
    parser.add_argument("--max-pages", type=int, default=10, help="最多翻多少页")
    parser.add_argument("--delay", type=float, default=0.5, help="详情页之间的等待秒数")
    parser.add_argument("--start-url", default=START_URL, help="起始列表页地址")
    parser.add_argument("--images", action="store_true", help="是否下载正文首图")
    parser.add_argument("--outdir", default="data", help="输出目录")
    parser.add_argument("--mysql", action="store_true", help="是否写入 MySQL")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="crawler_demo")
    crawl(parser.parse_args())


if __name__ == "__main__":
    main()
