# 中国新闻网滚动新闻爬虫（练习项目）

一个用于练习和面试展示的 Python 爬虫：抓取滚动新闻列表，进入详情页补齐字段，存 CSV，可选写入 MySQL、下载正文首图。

> 目标站点为中国新闻网滚动新闻页。抓取前已确认其 `robots.txt` 为 `Allow: /`（少数路径除外），本项目仅用于学习，请控制频率、不要用于商业用途。

## 功能

- 列表页翻页（`news1.html` → `news2.html` → …），空页自动停止
- 进入详情页补齐：完整发布时间、来源、正文长度、图片数量
- 自动跳过视频页、图集页等无正文页面
- 数据落 CSV（UTF-8 with BOM，Excel 直接打开不乱码）
- 可选写入 MySQL，按 `article_id` 去重
- 可选下载正文首图，用 `article_id` 命名
- 断点续爬：启动时读取已有 CSV，跳过已抓条目
- 请求超时、失败重试、请求限速、日志记录

## 目录结构

```
爬虫练习项目/
├── spider.py          # 主程序
├── requirements.txt   # 依赖
├── README.md
├── run_demo.bat       # Windows 双击运行（--limit 5）
├── .gitignore
└── data/              # 运行时生成
    ├── news.csv
    ├── spider.log
    └── images/
```

## 环境

- Python 3.11（项目内已建好 `.venv`）
- 依赖：requests、beautifulsoup4、lxml、pymysql

```powershell
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 运行

```powershell
# 先抓 5 条验证
python spider.py --limit 5

# 抓 3 页（约 300 条）
python spider.py --max-pages 3

# 同时下载首图
python spider.py --max-pages 2 --images

# 写入 MySQL
python spider.py --mysql --user root --password 你的密码 --database crawler_demo
```

参数：

| 参数 | 说明 | 默认 |
|---|---|---|
| `--limit` | 最多抓多少条，0 表示不限 | 0 |
| `--max-pages` | 最多翻多少页 | 10 |
| `--delay` | 详情页之间等待秒数 | 0.5 |
| `--start-url` | 起始列表页 | news1.html |
| `--images` | 是否下载正文首图 | 否 |
| `--outdir` | 输出目录 | data |
| `--mysql` | 是否写入 MySQL | 否 |

## MySQL 建表

```sql
CREATE DATABASE IF NOT EXISTS crawler_demo DEFAULT CHARSET utf8mb4;
USE crawler_demo;

CREATE TABLE IF NOT EXISTS news (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id   VARCHAR(32)  NOT NULL UNIQUE,
    title        VARCHAR(255) NOT NULL,
    category     VARCHAR(64),
    publish_time VARCHAR(64),
    list_time    VARCHAR(32),
    source       VARCHAR(64),
    content_len  INT,
    image_count  INT,
    image_url    VARCHAR(512),
    image_file   VARCHAR(255),
    url          VARCHAR(512),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 输出字段

| 字段 | 含义 |
|---|---|
| article_id | 新闻 ID，从 URL 提取，用于去重 |
| title | 标题 |
| category | 分类（社会 / 财经 / 视频 …） |
| publish_time | 详情页完整时间 |
| list_time | 列表页显示时间 |
| source | 来源媒体 |
| content_len | 正文长度（字符数） |
| image_count | 正文图片数量 |
| image_url / image_file | 首图地址 / 本地路径 |
| url | 详情页地址 |

## 常见问题

**返回 403**
先检查 User-Agent，再降低请求频率。

**页面里取不到数据**
站点改版或动态渲染。用 `print(soup.prettify()[:2000])` 打印 HTML 对照结构。

**中文乱码**
设置 `response.encoding = response.apparent_encoding`；CSV 用 `utf-8-sig`。

**抓到空标题**
详情页结构与列表页不同（如视频页）。本项目会跳过无正文页面；如需保留，可在合并时用列表页标题兜底。

**程序中途崩溃**
已对每条请求做 try/except，单条失败只记日志不中断。

## 可以讲的技术点（面试用）

1. 列表页 + 详情页两级抓取，`urljoin` 处理相对路径
2. 分页用 URL 规律递增，空页自动停止
3. 用 `article_id` 唯一键去重，CSV 断点续爬 + MySQL `ON DUPLICATE KEY UPDATE`
4. 超时、指数退避重试、请求限速
5. 图片用二进制 `response.content` 写入
6. 数据清洗：跳过无正文页面、字段统一、空值处理

## 免责声明

仅用于学习和技术练习。请遵守目标站点的 `robots.txt`、服务条款与相关法律法规，控制请求频率。
