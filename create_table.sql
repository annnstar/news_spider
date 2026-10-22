-- 建库建表脚本：mysql -u root -p < create_table.sql
CREATE DATABASE IF NOT EXISTS crawler_demo DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE crawler_demo;

CREATE TABLE IF NOT EXISTS news (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id   VARCHAR(32)  NOT NULL UNIQUE COMMENT '新闻ID，用于去重',
    title        VARCHAR(255) NOT NULL COMMENT '标题',
    category     VARCHAR(64)  COMMENT '分类',
    publish_time VARCHAR(64)  COMMENT '详情页完整时间',
    list_time    VARCHAR(32)  COMMENT '列表页时间',
    source       VARCHAR(64)  COMMENT '来源媒体',
    content_len  INT          COMMENT '正文长度',
    image_count  INT          COMMENT '图片数量',
    image_url    VARCHAR(512) COMMENT '首图地址',
    image_file   VARCHAR(255) COMMENT '本地图片路径',
    url          VARCHAR(512) COMMENT '详情页地址',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT '建表完成' AS result;
