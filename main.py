import argparse
import calendar
import json
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.header import Header
from email.mime.text import MIMEText


def getMonthlyFlow(year, month):
    begin_date = datetime.strptime('{0}-{1}'.format(year, month), '%Y-%m')
    begin_timestamp = begin_date.timestamp() * 1000
    days = calendar.monthrange(year, month)[1]
    end_date = begin_date + timedelta(days=days)
    end_timestamp = end_date.timestamp() * 1000

    sql = "select user.email, saveFlowDay.port as port, sum(saveFlowDay.flow)/1000000000.0 as flow from saveFlowDay " \
          "inner join account_plugin on saveFlowDay.accountId==account_plugin.id " \
          "inner join user on account_plugin.userId==user.id " \
          "where saveFlowDay.time between '{0}' and '{1}' " \
          "group by saveFlowDay.port".format(begin_timestamp, end_timestamp)

    return cursor.execute(sql)


def pretty(data, email=False):
    if email:
        return '<tr align=left><th align="left">{0:30s}</th><th align="left">{1:6d}</th><th align="left">{2:6.2f}G</th></tr>\n'.format(
            data[0], data[1], data[2])
    else:
        return '{email:30s}|{port:10d}|{usage:6.2f}G\n'.format(email=data[0], port=data[1], usage=data[2])


def send_mail(month, email, config):
    message = MIMEText(data, 'html')
    message['Subject'] = Header('SSMGR {0} 月用量'.format(month))
    message['From'] = config.get('mail_user')
    message['To'] = email

    smtp = smtplib.SMTP_SSL(config.get('mail_host'), config.get('mail_port'))
    smtp.login(config.get('mail_user'), config.get('mail_pass'))
    smtp.sendmail(config.get('mail_user'), email, message.as_string())


if __name__ == '__main__':
    now = datetime.now()
    date = datetime.strptime('{0}-{1}'.format(now.year, now.month), '%Y-%m')
    days = calendar.monthrange(date.year, date.month)[1]
    last_date = date - timedelta(days=days)

    parser = argparse.ArgumentParser(description='获取指定月份的SSMGR流量情况')
    parser.add_argument('-y', dest='year', metavar='year', type=int, nargs='?', default=last_date.year, help='查询年份')
    parser.add_argument('-m', dest='month', metavar='month', type=int, nargs='?', default=last_date.month, help='查询月份')
    parser.add_argument('-d', dest='db', metavar='database', type=str, nargs='?', default='webgui.sqlite',
                        help='WebGUI数据库')
    parser.add_argument('-e', dest='email', action='store_true', default=False, help='是否邮件发送')
    parser.add_argument('-c', dest='config_path', metavar='config_path', default='config.json', help='配置文件路径')
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    cursor = connection.cursor()
    with open(args.config_path, 'r') as f:
        config = json.load(f)

    if args.email:
        for row in getMonthlyFlow(args.year, args.month):
            data = '<html><body><table border="0">\n' \
                   '<tr><th align="left">邮箱</th><th align="left">端口</th><th align="left">用量</th></tr>\n'
            data += pretty(row, args.email)
            data += '</table></body></html>'
            send_mail(args.month, row[0], config)
    else:
        data = ''
        for row in getMonthlyFlow(args.year, args.month):
            data += pretty(row, args.email)
        print(data)

    cursor.close()
    connection.close()
