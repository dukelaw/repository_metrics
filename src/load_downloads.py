import argparse
import requests
import xlrd
import repository_metrics
from repository_metrics.model import (Article, Creator, Subject,
                                      Download, Discipline)
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from datetime import datetime


def excel_row_count(file_contents):
    """Count rows in the excel file"""
    workbook = xlrd.open_workbook(file_contents=file_contents)
    sheet = workbook.sheet_by_index(0)
    return sheet.nrows


def read_excel(file_contents, start_row=1, label_row=0, sheet_by_index=0):
    workbook = xlrd.open_workbook(file_contents=file_contents)
    #print workbook
    sheet = workbook.sheet_by_index(sheet_by_index)
    headers = sheet.row(label_row)
    labels = []
    for header in headers:
        if header.ctype in [2]:
            value = u"%d" % header.value
        elif header.ctype in [3]:
            value = xlrd.xldate_as_tuple(header.value, workbook.datemode)
        elif header.ctype in [4]:
            if header.value:
                value = True
            else:
                value = False
        else:
            value = header.value
        labels.append(value)

    for row_index in range(start_row, sheet.nrows):
        row = sheet.row(row_index)
        record = {}
        for (i, label) in enumerate(labels):
            # force floats DATE and NUMBER into a string
            if row[i].ctype in [2]:
                value = u"%d" % row[i].value
            elif row[i].ctype in [3]:
                value = xlrd.xldate_as_tuple(row[i].value, workbook.datemode)
            elif row[i].ctype in [4]:
                if row[i].value:
                    value = True
                else:
                    value = False
            else:
                value = row[i].value
            record[label] = value
        yield record


def get_spreadsheet(url):
    """Get the spreadsheet object from an URL"""
    try:
        request = requests.get(url)
        file_contents = request.content
    except:
        fh = open(url)
        file_contents = fh.read()
    return file_contents


def process_data(article, session, row):
    """Insert data"""
    if article.downloads:
        del article.downloads
        session.commit()
    for key, value in row.items():
        if isinstance(key, tuple):
            download_date = datetime(*key)
            download = Download(article_id=article.id,
                                download_date=download_date,
                                download_count=value)
            article.downloads.append(download)
    session.commit()
    return article


def main(args):
    session = repository_metrics.model.get_session()
    url = args.url
    file_contents = get_spreadsheet(url)
    i = 0
    for row in read_excel(file_contents, label_row=1, start_row=2):
        i += 1
        article_url = row['URL']
        query = session.query(Article).\
            filter(Article.article_url == article_url)
        article = None
        try:
            article = query.one()
        except:
            print(article_url)
            print("No article")
        if article:
            article = process_data(article, session, row)
        if i % 100 == 0:
            print("processing row: {0}".format(i))
            print(article_url)
            print(article)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Load XLS files and ' +
                                     'reshape into database schema')
    parser.add_argument('url', help="XLS file of monthly downloads")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    main(args)
