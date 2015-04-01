"""Schema for bibliographic and citation datbaase"""
import argparse
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UnicodeText, Integer, ForeignKey
from sqlalchemy import Unicode, Date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import ConfigParser
from nameparser import HumanName
from math import ceil
import os
import re
import unicodecsv


Base = declarative_base()


class Article(Base):
    """Article data"""
    __tablename__ = 'articles'

    __table_args__ = {'mysql_engine': 'InnoDB'}

    #column definitions
    id = Column(u'id', Integer, primary_key=True, nullable=False)
    title = Column(u'title', UnicodeText)
    submission_date = Column(u'submission_date', Date)
    date = Column('date', Date)
    document_type = Column(u'document_type', UnicodeText)
    article_url = Column(u'article_url', UnicodeText)
    oai_identifier = Column(u'oai_identifier', Unicode(255), unique=True)
    last_event = Column(u'last_event', UnicodeText)
    last_event_date = Column(u'last_event_date', Date)
    status = Column(u'status', Unicode(255))
    pdf_url = Column(u'pdf_url', UnicodeText)
    publication = Column(u'publication', UnicodeText, nullable=True)
    source_fulltext_url = Column(u'source_fulltext_url', UnicodeText)
    volume = Column(u'volume', UnicodeText(32))
    issue = Column(u'issue', UnicodeText(32))

    fpage = Column(u'fpage', UnicodeText(32))
    lpage = Column(u'lpage', UnicodeText(32))

    #relation definitions
    creators = relationship('Creator',
                            cascade="all, delete-orphan",
                            backref="article")
    subjects = relationship('Subject',
                            cascade="all, delete-orphan",
                            backref="article")
    disciplines = relationship('Discipline',
                               cascade="all, delete-orphan",
                               backref="article")
    downloads = relationship('Download',
                             cascade="all, delete-orphan",
                             backref="article")

    def __repr__(self):
        return u"<Article('%s, %s')>" % (self.id,
                                         self.oai_identifier)

    @property
    def byline(self):
        """Return a joined creator string"""
        stack = []
        if self.creators is None:
            return None
        for creator in self.creators:
            name = HumanName()
            name.first = creator.first
            name.last = creator.last
            name.middle = creator.middle
            name.suffix = creator.suffix
            stack.append(unicode(name))
        if len(stack) == 2:
            creator_string = u" and ".join(stack)
        elif len(stack) == 1:
            creator_string = stack[0]
        elif len(stack) > 2:
            last = stack.pop(-1)
            creator_string = u", ".join(stack)
            creator_string = creator_string + u' and ' + last
        else:
            creator_string = u""
        return creator_string

    @property
    def has_email(self):
        """Return True or False if it has an email address in authors"""
        for creator in self.creators:
            if creator.email:
                return True
        return False


class Creator(Base):
    """Creators for articles"""
    __tablename__ = 'creators'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    #column definitions
    article_id = Column(u'article_id', Integer,
                        ForeignKey('articles.id',
                                   ondelete='CASCADE',
                                   onupdate='CASCADE'),
                        primary_key=True)
    position = Column(u'position', Integer,
                      primary_key=True,
                      nullable=False, autoincrement=False)

    last = Column(u'last', UnicodeText)
    first = Column(u'first', UnicodeText)
    middle = Column(u'middle', UnicodeText)
    suffix = Column(u'suffix', UnicodeText)
    institution = Column(u'institution', Unicode(255))
    email = Column(u'email', Unicode(255), nullable=True)

    def __repr__(self):
        return u"<Creator('%s, %s')>" % (self.article_id, self.position)

    @property
    def name(self):
        """Returns name"""
        stack = []
        if self.last:
            stack.append(self.last)
        if self.first:
            stack.append(self.first)
        creator_string = u", ".join(stack)
        return creator_string


class Download(Base):
    """Downloads for articles"""
    __tablename__ = 'downloads'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    article_id = Column(u'article_id',
                        Integer,
                        ForeignKey('articles.id',
                                   ondelete='CASCADE',
                                   onupdate='CASCADE'),
                        nullable=False,
                        primary_key=True)
    # use yyyy-mm-01 for the month aggregations
    # Assume to support by day eventually
    download_date = Column(u'download_date', Date, primary_key=True)
    download_count = Column(u'download_count', Integer)

    def __repr__(self):
        return "<Download('{0} {1}')>".format(self.download_date,
                                              self.download_count)


class Subject(Base):
    """Subject class for articles"""
    __tablename__ = 'subjects'

    __table_args__ = {'mysql_engine': 'InnoDB'}

    #column definitions
    article_id = Column(u'article_id', Integer,
                        ForeignKey('articles.id',
                                   ondelete='CASCADE',
                                   onupdate='CASCADE'),
                        primary_key=True)
    position = Column(u'position',
                      Integer,
                      primary_key=True,
                      nullable=False,
                      autoincrement=False)
    term = Column(u'term', UnicodeText)

    def __repr__(self):
        return "<Subject('%s')>" % (self.term,)


class Discipline(Base):
    """Discipline class for articles"""
    __tablename__ = 'disciplines'

    __table_args__ = {'mysql_engine': 'InnoDB'}

    #column definitions
    article_id = Column(u'article_id', Integer,
                        ForeignKey('articles.id',
                                   ondelete='CASCADE',
                                   onupdate='CASCADE'),
                        primary_key=True)
    position = Column(u'position',
                      Integer,
                      primary_key=True,
                      nullable=False,
                      autoincrement=False)
    term = Column(u'term', UnicodeText)

    def __repr__(self):
        return "<Discipline('%s')>" % (self.term,)


class Pagination(object):
    """Pagination object"""
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        """Return the number of pages"""
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        """Return boolean"""
        return self.page > 1

    @property
    def has_next(self):
        """Return boolean"""
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Yield available page numbers"""
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               (num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def get_engine():
    """Return an sqlalchemy engine"""
    config_file = ConfigParser.ConfigParser()
    directory = os.path.dirname(os.path.realpath(__file__))
    config_file.read(os.path.join(directory, 'repository-metrics.cfg'))
    engine = create_engine(config_file.get("sqlalchemy", "dsn"),
                           echo=config_file.getboolean("sqlalchemy", "echo"),
                           pool_recycle=3600)
    return engine


def get_session():
    """Return a scoped session"""
    engine = get_engine()
    session = scoped_session(sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=engine))
    return session


def test():
    """Small testing framework"""
    print("Testing...")
    session = get_session()
    articles = session.query(Article)
    print(articles.count())

    article = session.query(Article).\
        filter(Article.oai_identifier.like('%faculty_scholarship-6024')).\
        one()

    print(article)
    print(article.byline)
    print(article.subjects)
    print(article.disciplines)
    print(article.creators)
    print(article.has_email)

    # get author
    creators = session.query(Creator).\
        filter(Creator.email == 'boyle@law.duke.edu')
    for creator in creators:
        print(creator.article)

    """
    query = session.query(Creator.email,
                          func.sum(Download.download_count).label('count')).\
        filter(Creator.email != None,
               Article.id == Creator.article_id,
               Article.id == Download.article_id).\
        group_by(Creator.email).\
        order_by(func.sum(Download.download_count).desc())
    for row in query:
        print(row)
    """


def generate_author_month_csv(output):
    """Generate csv for pivot"""
    session = get_session()
    print("making query")

    count = session.query(Article, Creator, Download).\
        filter(Creator.email != None).\
        filter(Article.id == Creator.article_id).\
        filter(Article.id == Download.article_id).\
        filter(Download.download_count > 0).count()
    print("rows: {0}".format(count))
    query = session.query(Article, Creator, Download).\
        filter(Creator.email != None).\
        filter(Article.id == Creator.article_id).\
        filter(Article.id == Download.article_id).\
        filter(Download.download_count > 0).yield_per(10000)
    fieldnames = ['email', 'creator', 'article_id', 'title', 'publication',
                  'publication_date', 'deposit_date', 'document_type',
                  'article_url', 'download_date', 'download_count']
    csvwriter = unicodecsv.DictWriter(open(output, 'wb'),
                                      fieldnames=fieldnames)
    csvwriter.writeheader()
    i = 0
    for (article, creator, download) in query:
        i += 1
        row = {}
        row['creator'] = creator.name
        row['article_id'] = article.id
        row['publication'] = article.publication
        row['publication_date'] = article.date
        row['deposit_date'] = article.submission_date
        row['email'] = creator.email
        row['title'] = article.title.strip()
        row['document_type'] = article.document_type
        row['article_url'] = article.article_url
        row['download_date'] = download.download_date
        row['download_count'] = download.download_count
        csvwriter.writerow(row)
        if i % 10000 == 0:
            print("writing row {0}".format(i))


def generate_articles_by_author_csv(output):
    session = get_session()
    print("making query")
    query = session.query(Creator).\
        filter(Creator.article_id == Article.id).yield_per(10000)
    fieldnames = ['email', 'creator', 'article_id', 'title', 'publication',
                  'publication_date', 'deposit_date', 'document_type',
                  'article_url', 'byline', 'constant']
    csvwriter = unicodecsv.DictWriter(open(output, 'wb'),
                                      fieldnames=fieldnames)
    csvwriter.writeheader()
    i = 0
    for creator in query:
        i += 1
        row = {}
        article = creator.article
        row['creator'] = creator.name
        row['article_id'] = article.id
        if article.publication:
            row['publication'] = article.publication.strip()
        row['publication_date'] = article.date
        row['deposit_date'] = article.submission_date
        row['email'] = creator.email
        row['title'] = article.title.strip()
        row['document_type'] = article.document_type
        row['article_url'] = article.article_url
        row['byline'] = article.byline
        csvwriter.writerow(row)
        if i % 1000 == 0:
            print("writing row {0}".format(i))


def generate_articles_month_csv(output):
    """Generate a table of one row per article/month downloads"""
    session = get_session()
    print("making query")
    fieldnames = ['article_id', 'download_date', 'title', 'byline',
                  'publication', 'publication_date', 'publication_year',
                  'deposit_date', 'document_type', 'context',
                  'article_url', 'has_faculty', 'download_count' ]

    csvwriter = unicodecsv.DictWriter(open(output, 'wb'),
                                      fieldnames=fieldnames)
    csvwriter.writeheader()
    query = session.query(Article).yield_per(100)
    i = 0
    for article in query:
        for download in article.downloads:
            row = {}
            i += 1
            row['article_id'] = article.id
            row['download_date'] = download.download_date
            row['title'] = article.title.strip()
            row['byline'] = article.byline
            if article.publication:
                row['publication'] = article.publication.strip()
            row['publication_date'] = article.date
            row['publication_year'] = article.date.year
            row['deposit_date'] = article.submission_date
            row['document_type'] = article.document_type

            # oai:scholarship.law.duke.edu:faculty_scholarship-5781
            context_re = re.compile('oai:scholarship.law.duke.edu' +
                                    ':([a-z_]+)-\d+')
            context_search = context_re.search(article.oai_identifier)
            if context_search:
                row['context'] = context_search.group(1)
            row['article_url'] = article.article_url
            row['has_faculty'] = article.has_email
            row['download_count'] = download.download_count
            csvwriter.writerow(row)
            if i % 1000 == 0:
                print("writing row {0}".format(i))


def generate_articles_csv(output):
    """Generate a table of article metadata"""
    session = get_session()
    print("making query")
    fieldnames = ['article_id', 'title', 'byline',
                  'publication', 'publication_date', 'publication_year',
                  'deposit_date', 'document_type', 'context',
                  'article_url', 'has_faculty']

    csvwriter = unicodecsv.DictWriter(open(output, 'wb'),
                                      fieldnames=fieldnames)
    csvwriter.writeheader()
    query = session.query(Article).yield_per(1000)
    i = 0
    for article in query:
        row = {}
        i += 1
        row['article_id'] = article.id
        row['title'] = article.title.strip()
        row['byline'] = article.byline
        if article.publication:
            row['publication'] = article.publication.strip()
        row['publication_date'] = article.date
        if article.date:
            row['publication_year'] = article.date.year
        row['deposit_date'] = article.submission_date
        row['document_type'] = article.document_type

        # oai:scholarship.law.duke.edu:faculty_scholarship-5781
        context_re = re.compile('oai:scholarship.law.duke.edu:([a-z_]+)-\d+')
        context_search = context_re.search(article.oai_identifier)
        if context_search:
            row['context'] = context_search.group(1)
        row['article_url'] = article.article_url
        row['has_faculty'] = article.has_email
        csvwriter.writerow(row)
        if i % 1000 == 0:
            print("writing row {0}".format(i))


def generate_faculty_scholarship_csv(output):
    """Generate a grouped view of faculty publications"""
    session = get_session()
    print("making query")
    fieldnames = ['article_id', 'download_date', 'title', 'byline',
                  'publication', 'publication_date', 'publication_year',
                  'deposit_date', 'document_type', 'context',
                  'article_url', 'has_faculty', 'download_count']

    csvwriter = unicodecsv.DictWriter(open(output, 'wb'),
                                      fieldnames=fieldnames)
    csvwriter.writeheader()
    faculty_scholarship = session.query(Article).\
        filter(Article.oai_identifier.like(u'%faculty_scholarship%')).\
        yield_per(100)
    i = 0
    j = 0
    seen_journal_articles = {}
    for article in faculty_scholarship:
        j += 1
        if j % 100 == 0:
            print("Starting article {0}: {1}".format(j, article.article_url))
        for download in article.downloads:
            row = {}
            i += 1
            # source_fulltext_url
            row['article_id'] = article.id
            row['title'] = article.title.strip()
            row['byline'] = article.byline
            if article.publication:
                row['publication'] = article.publication.strip()
            row['publication_date'] = article.date
            if article.date:
                row['publication_year'] = article.date.year
            row['deposit_date'] = article.submission_date
            row['document_type'] = article.document_type

            # oai:scholarship.law.duke.edu:faculty_scholarship-5781
            context_re = re.compile('oai:scholarship.law.duke.edu' +
                                    ':([a-z_]+)-\d+')
            context_search = context_re.search(article.oai_identifier)
            if context_search:
                row['context'] = context_search.group(1)
            row['article_url'] = article.article_url
            row['has_faculty'] = article.has_email
            row['download_date'] = download.download_date
            download_count = download.download_count
            if article.source_fulltext_url:
                seen_journal_articles[article.source_fulltext_url] = True
                try:
                    journal_download_count = session.query(Download
                                                           .download_count).\
                        filter(Article.pdf_url ==
                               article.source_fulltext_url).\
                        filter(Download.article_id == Article.id).\
                        filter(Download.download_date ==
                               download.download_date).\
                        scalar()
                    if journal_download_count:
                        download_count += journal_download_count
                except Exception as e:
                    print(e.msg)
            row['download_count'] = download_count
            csvwriter.writerow(row)
            if i % 1000 == 0:
                print("writing row {0}".format(i))
    print("Starting non_faculty")
    not_faculty_scholarship = session.query(Article).\
        filter(Article.oai_identifier.notlike(u'%faculty_scholarship%')).\
        filter(Article.id == Creator.article_id).\
        filter(Creator.email.contains('@')).\
        yield_per(100)
    for article in not_faculty_scholarship:
        j += 1
        if article.pdf_url in seen_journal_articles:
            print("Skipping: {0}".format(article.oai_identifier))
            continue
        if j % 100 == 0:
            print("Starting article {0}: {1}".format(j, article.article_url))
        for download in article.downloads:
            row = {}
            i += 1
            # source_fulltext_url
            row['article_id'] = article.id
            row['title'] = article.title.strip()
            row['byline'] = article.byline
            if article.publication:
                row['publication'] = article.publication.strip()
            row['publication_date'] = article.date
            if article.date:
                row['publication_year'] = article.date.year
            row['deposit_date'] = article.submission_date
            row['document_type'] = article.document_type

            # oai:scholarship.law.duke.edu:faculty_scholarship-5781
            context_re = re.compile('oai:scholarship.law.duke.edu' +
                                    ':([a-z_]+)-\d+')
            context_search = context_re.search(article.oai_identifier)
            if context_search:
                row['context'] = context_search.group(1)
            row['article_url'] = article.article_url
            row['has_faculty'] = article.has_email
            row['download_date'] = download.download_date
            download_count = download.download_count
            if article.source_fulltext_url:
                seen_journal_articles[article.source_fulltext_url] = True
                try:
                    journal_download_count = session.query(Download.download_count).\
                        filter(Article.pdf_url == article.source_fulltext_url).\
                        filter(Download.article_id == Article.id).\
                        filter(Download.download_date == download.download_date).\
                        scalar()
                    if journal_download_count:
                        download_count += journal_download_count
                except Exception as e:
                    print(e.msg)
            row['download_count'] = download_count
            csvwriter.writerow(row)
            if i % 1000 == 0:
                print("writing row {0}".format(i))


def create_tables():
    print("Creating tables...")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop the citation tables"""
    print("Dropping tables...")
    engine = get_engine()
    conn = engine.connect()
    database = conn.begin()
    tablenames = ['articles', 'creators', 'subjects', 'downloads',
                  'disciplines']
    try:
        conn.execute("SET foreign_key_checks = 0")
        database.commit()
    except:
        database.rollback()
    for tablename in tablenames:
        try:
            conn.execute("drop table {0}".format(tablename))
            database.commit()
        except:
            database.rollback()
        database = conn.begin()
    conn.close()
    return 1


def main(args):
    if args.droptables:
        drop_tables()
    elif args.createtables:
        create_tables()
    elif args.generate:
        generate_author_month_csv(args.output)
    elif args.authors:
        generate_articles_by_author_csv(args.output)
    elif args.articles:
        generate_articles_month_csv(args.output)
    elif args.article_summary:
        generate_articles_csv(args.output)
    elif args.faculty:
        generate_faculty_scholarship_csv(args.output)

    elif args.test:
        test()


def parse_arguments():
    """Command line utilities for model

    usage: model.py [-h] [-t] [-d] [-c]

    optional arguments:
      -h, --help           show this help message and exit
      -t, --test           Test session
      -d, --dropcitations  Drop tables
      -c, --createtables   Create tables"""
    parser = argparse.ArgumentParser(description="Command line utility " +
                                     "to access model")
    parser.add_argument("-t", "--test", help="Test session",
                        action="store_true")
    parser.add_argument("-D", "--droptables", help="Drop tables",
                        action="store_true", )
    parser.add_argument("-c", "--createtables", help="Create tables",
                        action="store_true")
    parser.add_argument("-g", "--generate", help="Author centered monthly",
                        action="store_true")
    parser.add_argument("-a", "--authors", help="Articles by author",
                        action="store_true")
    parser.add_argument("-A", "--articles", help="Article centered months",
                        action="store_true")
    parser.add_argument("-s", "--article_summary", help="Articles summary csv",
                        action="store_true")
    parser.add_argument("-F", "--faculty", help="Article centered faculty csv",
                        action="store_true")
    parser.add_argument("-o", "--output", help="Output filename",
                        default="/vagrant/output.csv")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    main(args)
