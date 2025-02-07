#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# 日志打印函数
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# 加载 .env 配置
load_dotenv("/root/tracker/config.env", override=True)

# 配置
EMAIL = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL").split(",")
SEARCH_URL = os.getenv("SEARCH_URL")
VIEW_SEARCH_URL = os.getenv("VIEW_SEARCH_URL")
LAST_REPORT_ID_FILE = os.getenv("LAST_REPORT_ID_FILE")
HEADERS = {
    "User-Agent": os.getenv("HEADERS_USER_AGENT"),
    "Referer": os.getenv("HEADERS_REFERER"),
    "Accept-Language": os.getenv("HEADERS_ACCEPT_LANGUAGE"),
    "Content-Type": os.getenv("HEADERS_CONTENT_TYPE"),
}

# 读取上次处理的报告 ID
def get_last_report_id():
    if LAST_REPORT_ID_FILE and os.path.exists(LAST_REPORT_ID_FILE):
        with open(LAST_REPORT_ID_FILE, "r") as file:
            return file.read().strip()
    return None

# 保存最新报告 ID
def save_last_report_id(report_id):
    if LAST_REPORT_ID_FILE:
        with open(LAST_REPORT_ID_FILE, "w") as file:
            file.write(report_id)
        log(f"已保存最新报告 ID: {report_id}")

# 发送邮件
def send_email(subject, attachment_content=None, attachment_name="report.pdf"):
    log(f"正在发送邮件到 {RECIPIENT_EMAIL}...")
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = "Undisclosed Recipients <noreply@example.com>"
    msg['Subject'] = subject
    msg['Bcc'] = ', '.join(RECIPIENT_EMAIL) if isinstance(RECIPIENT_EMAIL, list) else RECIPIENT_EMAIL


    # 附件
    if attachment_content:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_content)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={attachment_name}'
        )
        msg.attach(part)

    # 发送邮件
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
    log("邮件发送成功！")

# 查询最新报告
def search_for_report():
    log("正在查询符合条件的报告...")

    # 初始 GET 请求获取搜索页面
    session = requests.Session()
    session.get(VIEW_SEARCH_URL, headers=HEADERS)

    # 构造 POST 请求参数
    payload = {
    "LastName": "pelosi",
    "FilingYear": str(datetime.now().year)  # 动态获取当前年份
    }

    response = session.post(SEARCH_URL, headers=HEADERS, data=payload)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # 查找报告表格内容
    table_rows = soup.select("tbody tr")
    if not table_rows:
        log("未找到报告。")
        return None, None

    # 提取最后一个报告链接
    last_row = table_rows[-1]
    link_tag = last_row.find('a', href=True)
    if not link_tag:
        log("未找到报告链接。")
        return None, None

    report_url = link_tag['href']
    if not report_url.startswith("http"):
        report_url = f"https://disclosures-clerk.house.gov/{report_url.lstrip('/')}"

    report_id = report_url.split("/")[-1].replace(".pdf", "")

    return report_id, report_url

# 下载和发送报告
def download_and_send_report(report_id, report_url):
    log(f"正在从 {report_url} 下载报告...")
    pdf_response = requests.get(report_url, headers=HEADERS, stream=True)

    # 验证文件是否为PDF
    content_type = pdf_response.headers.get("Content-Type", "")
    if "pdf" not in content_type:
        log(f"下载的文件不是PDF: {content_type}")
        return

    attachment_content = pdf_response.content

    # 发送邮件
    send_email(
        subject=f"股神佩洛西 - {report_id}",
        attachment_content=attachment_content,
        attachment_name=f"{report_id}.pdf"
    )

    log(f"报告 {report_id} 已处理并发送。")

if __name__ == "__main__":
    last_report_id = get_last_report_id()
    report_id, report_url = search_for_report()

    if report_id and report_id != last_report_id:
        download_and_send_report(report_id, report_url)
        save_last_report_id(report_id)
    else:
        log("没有找到新的报告或报告未更新。")
