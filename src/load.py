"""Loader script for metadata and downloads"""
import argparse
import re
import requests
import urlparse
import xlrd
import repository_metrics
from repository_metrics.model import (Article, Creator, Subject,
                                      Discipline)
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


def excel_row_count(file_contents):
    """Count rows in the excel file"""
    workbook = xlrd.open_workbook(file_contents=file_contents)
    sheet = workbook.sheet_by_index(0)
    return sheet.nrows


def read_excel(file_contents):
    try:
        workbook = xlrd.open_workbook(file_contents=file_contents)
    except:
        workbook = None
    #print workbook
    if workbook:
        sheet = workbook.sheet_by_index(0)
        labels = sheet.row(0)
        for row_index in range(1, sheet.nrows):
            row = sheet.row(row_index)
            record = {}
            for (i, label) in enumerate(labels):
                # force floats DATE and NUMBER into a string
                if row[i].ctype in [2]:
                    value = u"%d" % row[i].value
                elif row[i].ctype in [3]:
                    value = xlrd.xldate_as_tuple(row[i].value,
                                                 workbook.datemode)
                elif row[i].ctype in [4]:
                    if row[i].value:
                        value = True
                    else:
                        value = False
                else:
                    value = row[i].value
                record[label.value] = value
            yield record


def get_spreadsheet(url):
    """Get the spreadsheet object from an URL"""
    request = requests.get(url)
    file_contents = request.content
    return file_contents


def get_metadata_report(server, context):
    """Pull the metadata report and make a datastructure for querying"""
    metadata = {}
    metadata_filename = "{0}_metadata.xls".format(context)
    metadata_report_url = urlparse.urljoin(server, metadata_filename)
    print("opening: {0}".format(metadata_report_url))
    for row in read_excel(get_spreadsheet(metadata_report_url)):
        # not everything has a calc_url
        if row['calc_url']:
            metadata[row['calc_url']] = row
    return metadata


def journal_context(context):
    mapping = {'alr': 'Alaska Law Review',
               'alr_onlineforum': 'Alaska Law Review Online Forum',
               'alr_yearinreview': 'Alaska Law Review Year in Review',
               'bernstein': 'Herbert L. Bernstein Memorial Lecture in ' +
                            'International and Comparative Law',
               'delpf': 'Duke Environmental Law & Policy Forum',
               'dflsc': 'Duke Forum for Law & Social Change',
               'dflsc_symposium': 'Duke Forum for Law & Social Change ' +
                                  '(Symposium)',
               'djcil': 'Duke Journal of Comparative & International Law',
               'djcil_online': 'Duke Journal of Comparative & International ' +
                               'Law Online',
               'djclpp': 'Duke Journal of Constitutional Law & Public Policy',
               'djclpp_sidebar': 'Duke Journal of Constitutional Law & ' +
                                 'Public Policy Sidebar',
               'djglp': 'Duke Journal of Gender Law & Policy',
               'dltr': 'Duke Law & Technology Review',
               'dlj': 'Duke Law Journal',
               'dlj_online': 'Duke Law Journal Online',
               'lcp': 'Law and Contemporary Problems'}
    return mapping.get(context)


def process_context(server, context, session):
    """Process files for each context"""
    editor_filename = "{0}_editor.xls".format(context)
    editor_report_url = urlparse.urljoin(server, editor_filename)
    metadata = get_metadata_report(server, context)
    print("opening: {0}".format(editor_report_url))
    for row in read_excel(get_spreadsheet(editor_report_url)):
        # update/create use oai_identifier
        oai_identifier = u"oai:scholarship.law.duke.edu:{0}-{1}".\
            format(context, row['Manuscript#'])
        pdf_url = u'http://scholarship.law.duke.edu/cgi/viewcontent.cgi?' +\
            'article={0}&context={1}'.format(row['Manuscript#'], context)
        article = None
        article_url = row['URL']
        title = row['Title'].strip()
        if article_url in metadata:
            row['metadata'] = metadata[article_url]  # stuff into row
        else:
            row['metadata'] = {}
        try:
            article = session.query(Article).\
                filter(Article.oai_identifier == oai_identifier).one()
        except NoResultFound, e:
            article = Article(title=title, article_url=row['URL'],
                              oai_identifier=oai_identifier, pdf_url=pdf_url)
        except MultipleResultsFound, e:
            print e

        # article.submission_date
        article.submission_date = row['Submission date']
        # article.date
        if 'Date posted' in row:
            article.date = row['Date posted']
        elif 'Date published' in row:
            article.date = row['Date published']

        if 'Submission type' not in row:
            article.document_type = u'Other'
        else:
            article.document_type = row['Submission type']

        article.last_event = row['Last event']
        article.last_event_date = row['Date of last event']

        # article status
        article.status = row['Status']

        if 'Volume' in row:
            article.volume = row['Volume']
        elif 'volnum' in row['metadata']:
            article.volume = row['metadata']['volnum']

        if 'Issue' in row:
            article.issue = row['Issue']
        elif 'issnum' in row['metadata']:
            article.issue = row['metadata']['issnum']

        if 'fpage' in row['metadata']:
            article.fpage = row['metadata']['fpage']

        if 'lpage' in row['metadata']:
            article.lpage = row['metadata']['lpage']
        if context == 'faculty_scholarship' and row.get('metadata'):
            source_publication = row['metadata']['source_publication']
            if source_publication:
                article.publication = source_publication.strip()
            else:
                article.publication = None
            # add reference to journal version
            source_fulltext_url = row['metadata']['source_fulltext_url']
            if source_fulltext_url:
                article.source_fulltext_url = source_fulltext_url.strip()
            else:
                article.source_fulltext_url = None
        else:
            article.publication = journal_context(context)
        # add creators
        # Author 1 Institution	Author 1 Email
        i = 1
        creator_key = 'Author {0}'.format(i)
        creators = []
        while "{0} First Name".format(creator_key) in row:
            elementnames = ['First Name', 'Middle Name', 'Last Name',
                            'Suffix', 'Institution', 'Email']
            creator = Creator()
            for elementname in elementnames:
                elementkey = "{0} {1}".format(creator_key, elementname)
                value = row[elementkey]
                attname = elementname.lower().replace(' name', '')
                setattr(creator, attname, value)
            if creator.first or creator.last:
                if not creator.email:
                    creator.email = None
                creators.append(creator)
            i += 1
            creator_key = 'Author {0}'.format(i)

        if article.creators:
            del article.creators
            session.commit()
        for j, creator in enumerate(creators):
            creator.position = j + 1
            article.creators.append(creator)

        # keywords
        keywords = re.split(',\s*', row['Keywords'])
        try:
            keywords.remove('')
        except:
            pass
        if article.subjects:
            del article.subjects
            session.commit()
        if len(keywords) > 0:
            for j, keyword in enumerate(keywords):
                subject = Subject(article_id=article.id, position=j + 1,
                                  term=keyword)
                article.subjects.append(subject)

        # disciplines
        if row['metadata']:
            if article.disciplines:
                del article.disciplines
                session.commit()
            terms = re.split(';\s*', row['metadata']['disciplines'])
            try:
                terms.remove('')
            except:
                pass
            if len(terms) > 0:
                for j, term in enumerate(terms):
                    discipline = Discipline(article_id=article.id,
                                            position=j + 1,
                                            term=term)
                    article.disciplines.append(discipline)
        session.add(article)
        session.commit()
        # deal with creators
    return True


def main(args):
    session = repository_metrics.model.get_session()
    server = args.server
    contexts = args.contexts
    for context in contexts:
        process_context(server, context, session)
    return 0


def parse_arguments():
    contexts = ['alr', 'bernstein', 'delpf', 'dflsc', 'dflsc_symposium',
                'djcil', 'djcil_online', 'djclpp', 'djclpp_sidebar', 'djglp',
                'dlj', 'dlj_online', 'dltr', 'alr_onlineforum',
                'alr_yearinreview', 'studentpapers', 'lcp', 'working_papers',
                'etd', 'faculty_scholarship']
    parser = argparse.ArgumentParser(description='Load XLS files and ' +
                                     'reshape into database schema')
    parser.add_argument('server', help="Server address and path for data " +
                        "files to load")
    parser.add_argument('contexts', help="Publication context or series",
                        nargs="*", default=contexts)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    main(args)
