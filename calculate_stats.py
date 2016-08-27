#!/usr/bin/env python

import re
import sys
import csv
import operator
import datetime

# TODO:
#
# Figure out how to get a multiline table working for most read author list.
# See the appropriate section for some clues.
#
# Remove articles (The) from series list for sorting purposes.
#
# Review German-language authors for nationality: Joseph Roth???

class Book:
    """A description of a book"""
    def __init__(self, title, print_author, year, reftitle):
        self.title = title
        self.print_author = print_author
        self.print_year = year
        # Turn BCE into a negative number.
        if re.search(r'B\.C\.E\.', year):
            year = re.sub(r'([0-9]*) B\.C\.E\.', r'-\1', year)
        self.year = int(year)
        self.reftitle = reftitle
        self.country = ''
        self.novel = False # derived in post-processing
        self.nonfiction = False
        self.collection = False
        self.novella = False
        self.shortstory = False
        self.play = False
        self.epicpoem = False
        self.poetry = False
        self.graphicnovel = False
        self.published = (0, 0)
        self.series = ''
        self.series_index = 0
        self.sequel_of = ''
        self.language = 'English' # original language
        self.authors = [] # list of Author records
        self.reading = [] # list of Reading records
        self.score = 0

class Reading:
    """A record of a specific reading of a book"""
    def __init__(self, book, dates, german, german_trans, translated,
            translator, unfinished, unknown, read_num):
        self.book = book # the associated Book record
        self.date_strs = dates # (start, finish), use zeros for unknown/uncertain/unfinished
        self.german = german
        self.german_trans = german_trans # English translation of German title
                                         # Should this be part of the Book?
                                         # Beware of rereadings that use germansame...
        self.translated = translated
        self.translator = translator
        self.unfinished = unfinished
        self.unknown = unknown # Dates read unknown
        self.read_num = read_num # nth reading of the book (1 = first, 2 = re-reading, etc.)
        self.ordering = 0
        self.year_read = 0 # Derived in post-processing
        # Construct date structs for comparison purposes.
        self.dates = []
        for date in dates:
            if date == 0:
                date = datetime.date(1, 1, 1)
            else:
                dateparts = str(date).split('.')
                if len(dateparts) == 1:
                    date = datetime.date(int(dateparts[0]), 1, 1)
                elif len(dateparts) == 2:
                    date = datetime.date(int(dateparts[0]), int(dateparts[1]), 1)
                else:
                    date = datetime.date(int(dateparts[0]), int(dateparts[1]), int(dateparts[2]))
            self.dates.append(date)
        if len(self.dates) == 2:
            self.duration = self.dates[1] - self.dates[0]
        else:
            self.duration = []

    def read_cmp(self, other):
        # If no explicit ordering was provided for both readings, use date
        # structs. (Python3 does not make relying on the date strings feasible.)
        # If the book was unfinished, just use the start date; this is
        # accomplished by using the max of the dates.
        if self.ordering == 0 and other.ordering == 0:
            if max(self.dates) > max(other.dates):
                return 1
            elif max(self.dates) < max(other.dates):
                return -1
            else:
                return 0
        elif self.ordering == 0:
            return 1
        elif other.ordering == 0:
            return -1
        elif self.ordering > other.ordering:
            return 1
        elif self.ordering < other.ordering:
            return -1
        else:
            return 0

    # Support both python2 and python3, albeit rather inefficiently.
    def __cmp__(self, other):
        return self.read_cmp(other)
    def __lt__(self, other):
        return self.read_cmp(other) < 0
    def __gt__(self, other):
        return self.read_cmp(other) > 0
    def __eq__(self, other):
        return self.read_cmp(other) == 0

class Author:
    """A description of a single author"""
    def __init__(self, sort_name, print_name):
        # Underscores should be used in sort_name to connect multi-word last
        # names. Assume that the last word of the name is the complete last name
        # and rearrange accordingly. If there are no spaces, treat the whole
        # name as the last name.
        self.label_name = sort_name
#        star_index = sort_name.find('*')
#        if star_index >= 0:
#            self.sort_name = sort_name[star_index + 1:].strip() + ', ' + sort_name[:star_index]
#        else:
        space_index = sort_name.rfind(' ')
        if space_index >= 0:
            self.sort_name = sort_name[space_index + 1:].strip() + ', ' + sort_name[:space_index]
        else:
            self.sort_name = sort_name
        self.print_name = print_name
        self.books = [] # list of Book records (written by this author)


def main():
    file = open("book_reviews.tex", "r")
    init = False
    books = []
    readings = []
    authors = []
    new_reading = False
    temp_author_sort = ''
    temp_author_print = ''
    temp_german = False
    temp_german_trans = ''
    temp_translated = False
    temp_translator = ''

    for line in file:
        if re.search(r'calc_stats_from_here', line):
            init = True
        elif init is False:
            continue
        elif re.search(r'\\booktitle', line):
            if books:
                # Do a bit of work on the author(s) of the previous before starting
                # the next one. If an extra author line wasn't provided, just use
                # the entry from the booktitle line. 
                if not temp_author_sort:
                    temp_author_sort = author
                    temp_author_print = author
                # Parse the author strings and add to the author list if not there.
                # Returns the individual authors.
                book_authors = parse_authors(authors, temp_author_sort, temp_author_print)
                # Add each author to the book's list of authors, and add the book to
                # each author's list of books.
                for author in book_authors:
                    book.authors.append(author)
                    author.books.append(book)
                temp_author_sort = ''
                temp_author_print = ''
                # Assume any book that doesn't fit into another category is a novel.
                if book.nonfiction == False and book.collection == False and \
                        book.novella == False and book.shortstory == False and \
                        book.play == False and book.epicpoem == False and \
                        book.poetry == False and book.graphicnovel == False:
                    book.novel = True
            # Now for the new book entry!
            line = fix_special_characters(line)
            # Remove backslashes before periods and ampersands.
            line = re.sub(r'\.\\ ', r'. ', line)
            line = re.sub(r' \\& ', r' & ', line)
            title_line = line[:-1].split('{')
            title = title_line[1][:-1]
            author = title_line[2][:-1]
            year = title_line[3][:-1]
            if re.search(r'\\booktitlelabel', line):
                # Also matches booktitlelabelauthor.
                reftitle = title_line[4][:-1]
            else:
                reftitle = title
            if re.search(r'\\booktitleauthortwo', line):
                # Assume these author names are safe for labels for now.
                temp_author_sort = title_line[4][:-1] + ' & ' + title_line[5][:-1]
                temp_author_print = temp_author_sort
            elif re.search(r'\\booktitleauthorfive', line):
                # Assume these author names are safe for labels for now.
                temp_author_sort = title_line[4][:-1] + ' & ' + title_line[5][:-1] + ' & ' + title_line[6][:-1] + ' & ' + title_line[7][:-1] + ' & ' + title_line[8][:-1]
                temp_author_print = temp_author_sort
            elif re.search(r'\\booktitleauthor', line):
                temp_author_sort = title_line[4][:-1]
                temp_author_print = author
            elif re.search(r'\\booktitlelabelauthor', line):
                temp_author_sort = title_line[5][:-1]
                temp_author_print = author
            book = Book(title, author, year, reftitle)
            books.append(book)
            new_reading = True
#        elif re.search(r'\\authorfix', line):
#            line = fix_special_characters(line)
#            author_line = line[:-1].split('{')
#            temp_author_sort = author_line[1][:-1]
#            temp_author_print = author_line[2][:-1]
        elif re.search(r'\\country', line):
            book.country = line[:-1].split('{')[1][:-1]
        elif re.search(r'\\nonfiction', line):
            book.nonfiction = True
        elif re.search(r'\\collection', line):
            book.collection = True
        elif re.search(r'\\novella', line):
            book.novella = True
        elif re.search(r'\\shortstory', line):
            book.shortstory = True
        elif re.search(r'\\play', line):
            book.play = True
        elif re.search(r'\\epicpoem', line):
            book.epicpoem = True
        elif re.search(r'\\poetry', line):
            book.poetry = True
        elif re.search(r'\\graphicnovel', line):
            book.graphicnovel = True
        elif re.search(r'\\published', line):
            pub_line = line[:-1].split('{')
            book.published = (int(pub_line[1][:-1]), int(pub_line[2][:-1]))
        elif re.search(r'\\series', line):
            series_line = line[:-1].split('{')
            # Ignore number of books in the series (if it is specified).
            book.series = series_line[1][:-1]
            book.series_index = int(series_line[2][:-1])
        elif re.search(r'\\sequel', line):
            book.sequel_of = line[:-1].split('{')[1][:-1]
        elif re.search(r'\\germansame', line):
            temp_german = True
            book.language = 'German'
        elif re.search(r'\\german', line):
            temp_german = True
            temp_german_trans = line[:-1].split('{')[1][:-1]
            book.language = 'German'
        elif re.search(r'\\translated', line):
            # Remove backslashes before periods and ampersands.
            line = re.sub(r'\.\\ ', r'. ', line)
            line = re.sub(r' \\& ', r' & ', line)
            trans_line = line[:-1].split('{')
            temp_translated = True
            # Language is a feature of a book, not of a particular reading of
            # it, but currently I have it associated with a given translation.
            # Presumably, if I re-read it, the language would not change.
            book.language = trans_line[1][:-1]
            temp_translator = trans_line[2][:-1]
        elif re.search(r'\\dates', line):
            date_line = line[:-1].split('{')
            dates = (date_line[1][:-1], date_line[2][:-1])
            unfinished = False
            unknown = False
            reading = Reading(book, dates, temp_german, temp_german_trans,
                    temp_translated, temp_translator, unfinished, unknown,
                    len(book.reading) + 1)
            book.reading.append(reading)
            new_reading = True
        elif re.search(r'\\finished', line):
            dates = (0, line[:-1].split('{')[1][:-1])
            unfinished = False
            unknown = False
            reading = Reading(book, dates, temp_german, temp_german_trans,
                    temp_translated, temp_translator, unfinished, unknown,
                    len(book.reading) + 1)
            book.reading.append(reading)
            new_reading = True
        elif re.search(r'\\unfinished', line):
            dates = (line[:-1].split('{')[1][:-1], 0)
            unfinished = True
            unknown = False
            reading = Reading(book, dates, temp_german, temp_german_trans,
                    temp_translated, temp_translator, unfinished, unknown,
                    len(book.reading) + 1)
            book.reading.append(reading)
            new_reading = True
        elif re.search(r'\\uncertain', line) or re.search(r'\\unknown', line):
            dates = (0, 0)
            if re.search(r'\\unknownunfinished', line):
                unfinished = True
            else:
                unfinished = False
            if re.search(r'\\unknown', line):
                unknown = True
            else:
                unknown = False
            reading = Reading(book, dates, temp_german, temp_german_trans,
                    temp_translated, temp_translator, unfinished, unknown,
                    len(book.reading) + 1)
            book.reading.append(reading)
            new_reading = True
        elif re.search(r'\\rereading', line):
            # Assume that the counter is set through the date fields, so we
            # don't really need to use this flag/command for anything.
            new_reading = True
        elif re.search(r'\\ordering', line):
            reading.ordering = int(line[:-1].split('{')[1][:-1])
        elif re.search(r'\\score', line):
            book.score = int(line[:-1].split('{')[1][:-1])

        if new_reading:
            temp_german = False
            temp_german_trans = ''
            temp_translated = False
            temp_translator = ''
            new_reading = False

    print('Number of books read: ', len(books))
    for book in books:
        for reading in book.reading:
            readings.append(reading)
    print('Number including rereadings: ', len(readings))

    readings = sorted(readings, reverse=True)

    this_year = datetime.datetime.now().year
    min_year_read = this_year

    # Print csv file to mimic the original spreadsheet. Python 3 can write in
    # Unicode, which means the special characters translate correctly, but
    # Python 2 cannot.
    if sys.version_info >= (3, 0):
        csvfile = open('booklist.csv', 'w', newline='', encoding='utf-8')
    else:
        csvfile = open('booklist.csv', 'w')
    csv_out = csv.writer(csvfile, 'excel')
    # Write out header row.
    csv_out.writerow(['Date Began', 'Date Read', 'Author', 'Title',
        'Translator', 'Published', 'Score', 'Country', 'German', 'Nonfiction',
        'Novella', 'Collection', 'Short Story', 'Play', 'Epic Poem', 'Poetry',
        'Graphic Novel', 'Re-Reading', 'Sequel Of', 'Series'])

    for reading in reversed(readings):
        newdates = []
        for date in reading.date_strs:
            # Build date strings for CSV/Excel display.
            dateparts = str(date).split('.')
            if len(dateparts) == 3:
                newdates.append(dateparts[1] + '/' + dateparts[2] + '/' + dateparts[0])
            elif len(dateparts) == 2:
                newdates.append(dateparts[1] + '/' + dateparts[0])
            elif reading.unfinished and len(newdates) >= 1:
                if reading.unknown:
                    newdates.append('??? ---')
                else:
                    newdates.append('---')
            elif reading.unknown and len(newdates) >= 1:
                newdates.append('???')
            elif len(dateparts) == 1:
                if dateparts[0] == '0':
                    newdates.append('')
                else:
                    newdates.append(dateparts[0])
            else:
                newdates.append('')

            # Calcuate year read. Use greater value of the two dates. Ignore
            # zero values.
            if len(dateparts) >= 1 and int(dateparts[0]) > 0:
                reading.year_read = max(int(dateparts[0]), reading.year_read)
                # Keep track of minimum year read.
                if reading.year_read < min_year_read:
                    min_year_read = reading.year_read

        print_year = re.sub(r'([0-9]*) B\.C\.E\.', r'-\1', str(reading.book.year))

        if reading.book.score <= 0:
            print_score = ''
        else:
            print_score = reading.book.score

        if reading.german:
            print_german = 'Y'
        else:
            print_german = ''
        if reading.book.nonfiction:
            print_nonfiction = 'Y'
        else:
            print_nonfiction = ''
        if reading.book.novella:
            print_novella = 'Y'
        else:
            print_novella = ''
        if reading.book.collection:
            print_collection = 'Y'
        else:
            print_collection = ''
        if reading.book.shortstory:
            print_shortstory = 'Y'
        else:
            print_shortstory = ''
        if reading.book.play:
            print_play = 'Y'
        else:
            print_play = ''
        if reading.book.epicpoem:
            print_epicpoem = 'Y'
        else:
            print_epicpoem = ''
        if reading.book.poetry:
            print_poetry = 'Y'
        else:
            print_poetry = ''
        if reading.book.graphicnovel:
            print_graphicnovel = 'Y'
        else:
            print_graphicnovel = ''

        if len(reading.book.reading) > 1:
            print_read_num = reading.read_num
        else:
            print_read_num = ''

        csv_out.writerow([newdates[0], newdates[1], reading.book.print_author,
            reading.book.title, reading.translator, print_year, print_score,
            reading.book.country, print_german, print_nonfiction, print_novella,
            print_collection, print_shortstory, print_play, print_epicpoem,
            print_poetry, print_graphicnovel, print_read_num,
            reading.book.sequel_of, reading.book.series])

    # Initialize list of years finished. Add an extra slot for early unknown
    # dates.
    num_years_read = this_year - min_year_read + 2
    finished_by_year = [0] * num_years_read
    unfinished_by_year = [0] * num_years_read
    german_by_year = [0] * num_years_read
    reread_by_year = [0] * num_years_read
    nonfiction_by_year = [0] * num_years_read
    collections_by_year = [0] * num_years_read
    novellas_by_year = [0] * num_years_read
    shorts_by_year = [0] * num_years_read
    plays_by_year = [0] * num_years_read
    epics_by_year = [0] * num_years_read
    poetry_by_year = [0] * num_years_read
    graphic_by_year = [0] * num_years_read
    novels_by_year = [0] * num_years_read

    # Re-iterate through readings to calculate number of books read per year.
    for reading in readings:
        if reading.year_read == 0:
            temp_year = 0
        else:
            temp_year = reading.year_read - min_year_read + 1
        finished_by_year[temp_year] = finished_by_year[temp_year] + 1
        if reading.unfinished:
            unfinished_by_year[temp_year] = unfinished_by_year[temp_year] + 1
        if reading.german:
            german_by_year[temp_year] = german_by_year[temp_year] + 1
        if reading.read_num > 1:
            reread_by_year[temp_year] = reread_by_year[temp_year] + 1
        if reading.book.nonfiction:
            nonfiction_by_year[temp_year] = nonfiction_by_year[temp_year] + 1
        elif reading.book.collection:
            collections_by_year[temp_year] = collections_by_year[temp_year] + 1
        elif reading.book.novella:
            novellas_by_year[temp_year] = novellas_by_year[temp_year] + 1
        elif reading.book.shortstory:
            shorts_by_year[temp_year] = shorts_by_year[temp_year] + 1
        elif reading.book.play:
            plays_by_year[temp_year] = plays_by_year[temp_year] + 1
        elif reading.book.epicpoem:
            epics_by_year[temp_year] = epics_by_year[temp_year] + 1
        elif reading.book.poetry:
            poetry_by_year[temp_year] = poetry_by_year[temp_year] + 1
        elif reading.book.graphicnovel:
            graphic_by_year[temp_year] = graphic_by_year[temp_year] + 1
        else:
            # Assume anything not in any other category is a novel.
            novels_by_year[temp_year] = novels_by_year[temp_year] + 1

    pub_bce = 0
    pub_1_1000 = 0
    pub_1001_1500 = 0
    pub_16th = 0
    pub_17th = 0
    pub_18th = 0
    pub_19th = 0
    pub_1900s = 0
    pub_1910s = 0
    pub_1920s = 0
    pub_1930s = 0
    pub_1940s = 0
    pub_1950s = 0
    pub_1960s = 0
    pub_1970s = 0
    pub_1980s = 0
    pub_1990s = 0
    pub_2000s = 0
    pub_2010s = 0
    countries = dict()
    languages = dict()
    scores = [0] * 6
    series_dict = dict()
#    authors = dict()

    for book in books:
        # For poetry and collections of works that have original publication
        # dates different than the collection's publication date, use the
        # midpoint of the original publication range. A bit rough, but certainly
        # better than using the collection's date, which may be decades or
        # centuries after the fact.
        if book.published[0] > 0 and book.published[1] > 0:
            year = (book.published[0] + book.published[1]) // 2
        else:
            year = book.year

        if year < 0:
            pub_bce = pub_bce + 1
        elif year <= 1000:
            pub_1_1000 = pub_1_1000 + 1
        elif year <= 1500:
            pub_1001_1500 = pub_1001_1500 + 1
        elif year <= 1600:
            pub_16th = pub_16th + 1
        elif year <= 1700:
            pub_17th = pub_17th + 1
        elif year <= 1800:
            pub_18th = pub_18th + 1
        elif year <= 1900:
            pub_19th = pub_19th + 1
        elif year <= 1910:
            pub_1900s = pub_1900s + 1
        elif year <= 1920:
            pub_1910s = pub_1910s + 1
        elif year <= 1930:
            pub_1920s = pub_1920s + 1
        elif year <= 1940:
            pub_1930s = pub_1930s + 1
        elif year <= 1950:
            pub_1940s = pub_1940s + 1
        elif year <= 1960:
            pub_1950s = pub_1950s + 1
        elif year <= 1970:
            pub_1960s = pub_1960s + 1
        elif year <= 1980:
            pub_1970s = pub_1970s + 1
        elif year <= 1990:
            pub_1980s = pub_1980s + 1
        elif year <= 2000:
            pub_1990s = pub_1990s + 1
        elif year <= 2010:
            pub_2000s = pub_2000s + 1
        else:
            pub_2010s = pub_2010s + 1

        if book.country in countries:
            countries[book.country] = countries[book.country] + 1
        else:
            countries[book.country] = 1

        if book.language in languages:
            languages[book.language] = languages[book.language] + 1
        else:
            languages[book.language] = 1

        # Score of 0 means undecided/unknown.
        scores[book.score] = scores[book.score] + 1

        if len(book.series) > 0:
            if book.series in series_dict:
                series_dict[book.series] = series_dict[book.series] + 1
            else:
                series_dict[book.series] = 1

#        if book.author in authors:
#            authors[book.author] = authors[book.author] + 1
#        else:
#            authors[book.author] = 1

#    print(pub_bce, pub_1_1000, pub_1001_1500, pub_16th, pub_17th, pub_18th,
#            pub_19th, pub_1900s, pub_1910s, pub_1920s, pub_1930s, pub_1940s,
#            pub_1950s, pub_1960s, pub_1970s, pub_1980s, pub_1990s, pub_2000s,
#            pub_2010s)


    stat_file = open('statistics.tex', 'w')
    stat_file.write('\\hyperref[sec:pubdate]{Books Read per Publication Year} \dotfill \pageref{sec:pubdate}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:finished_date]{Books Read per Year} \dotfill \pageref{sec:finished_date}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:unfinished_list]{List of Unfinished Books} \dotfill \pageref{sec:unfinished_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:rereading_list]{List of Re-read Books} \dotfill \pageref{sec:rereading_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:finished_category]{Books Read per Year by Category} \dotfill \pageref{sec:finished_category}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:category_list]{List of Books per Category} \dotfill \pageref{sec:category_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:country_table]{Books Read per Country} \dotfill \pageref{sec:country_table}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:country_list]{List of Books per Country} \dotfill \pageref{sec:country_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:language_table]{Books Read per Language} \dotfill \pageref{sec:language_table}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:language_list]{List of Books per Language} \dotfill \pageref{sec:language_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:score_table]{Books Read per Score} \dotfill \pageref{sec:score_table}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:score_list]{List of Books per Score} \dotfill \pageref{sec:score_list}\n')
    for x in reversed(range(6)):
        stat_file.write('\\\\\\indent\\indent\\hyperref[sec:score' + str(x) + ']')
        if x == 0:
            stat_file.write('{Unscored}')
        else:
            stat_file.write('{Score of ' + str(x) + '}')
        stat_file.write(' \dotfill \pageref{sec:score' + str(x) + '}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:series_list]{List of Series} \dotfill \pageref{sec:series_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:author_table]{Most Read Authors} \dotfill \pageref{sec:author_table}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:author_list]{List of Authors} \dotfill \pageref{sec:author_list}\n')
    stat_file.write('\\\\\\indent\\hyperref[sec:duration_list]{List of Books by Duration} \dotfill \pageref{sec:duration_list}\n')
    stat_file.write('\n')


    # Books per millenium/century/decade of publication.
    stat_file.write('\\subsection*{Number of books read per era/decade of original publication, not counting re-readings} \\label{sec:pubdate}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{era/decade} & \\textit{number read} \\\\ \\hline\n')
    stat_file.write('  B.C.E. & ' + str(pub_bce) + ' \\\\ \\hline\n')
    stat_file.write('  1-1000 & ' + str(pub_1_1000) + ' \\\\ \\hline\n')
    stat_file.write('  1001-1500 & ' + str(pub_1001_1500) + ' \\\\ \\hline\n')
    stat_file.write('  1501-1600 & ' + str(pub_16th) + ' \\\\ \\hline\n')
    stat_file.write('  1601-1700 & ' + str(pub_17th) + ' \\\\ \\hline\n')
    stat_file.write('  1701-1800 & ' + str(pub_18th) + ' \\\\ \\hline\n')
    stat_file.write('  1801-1900 & ' + str(pub_19th) + ' \\\\ \\hline\n')
    stat_file.write('  1901-1910 & ' + str(pub_1900s) + ' \\\\ \\hline\n')
    stat_file.write('  1911-1920 & ' + str(pub_1910s) + ' \\\\ \\hline\n')
    stat_file.write('  1921-1930 & ' + str(pub_1920s) + ' \\\\ \\hline\n')
    stat_file.write('  1931-1940 & ' + str(pub_1930s) + ' \\\\ \\hline\n')
    stat_file.write('  1941-1950 & ' + str(pub_1940s) + ' \\\\ \\hline\n')
    stat_file.write('  1951-1960 & ' + str(pub_1950s) + ' \\\\ \\hline\n')
    stat_file.write('  1961-1970 & ' + str(pub_1960s) + ' \\\\ \\hline\n')
    stat_file.write('  1971-1980 & ' + str(pub_1970s) + ' \\\\ \\hline\n')
    stat_file.write('  1981-1990 & ' + str(pub_1980s) + ' \\\\ \\hline\n')
    stat_file.write('  1991-2000 & ' + str(pub_1990s) + ' \\\\ \\hline\n')
    stat_file.write('  2001-2010 & ' + str(pub_2000s) + ' \\\\ \\hline\n')
    stat_file.write('  2011-2020 & ' + str(pub_2010s) + ' \\\\ \\hline\n')
    stat_file.write('  total & ' + str(len(books)) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')


    # Books read per year, including unfinished, German, and rereadings.
    stat_file.write('\\subsection*{Number of books read per year} \\label{sec:finished_date}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|l|l|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{year} & \\textit{count} & ' +
            '\\textit{\hyperref[sec:unfinished_list]{unfinished}} & ' +
            '\\textit{German} & \\textit{\hyperref[sec:rereading_list]{rereading}} \\\\ \\hline\n')
    for x in range(num_years_read):
        if x == 0:
            stat_file.write('  Unknown')
        else:
            stat_file.write('  ' + str(min_year_read + x - 1))
        stat_file.write(' & ' + str(finished_by_year[x]) + ' & ' + str(unfinished_by_year[x]) + ' & ' + str(german_by_year[x]) + ' & ' + str(reread_by_year[x]) + ' \\\\ \\hline\n')
    # Print totals of all years.
    stat_file.write('  total & ' + str(len(readings)) + ' & ' + str(sum(unfinished_by_year)) + ' & ' + str(sum(german_by_year)) + ' & ' + str(sum(reread_by_year)) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    # List of unfinished books
    stat_file.write('\\subsection*{List of unfinished books} \\label{sec:unfinished_list}\n\n')
    counter = 1
    for reading in (reading for reading in readings if reading.unfinished == True):
        title = re.sub(r' & ', r' \& ', reading.book.title)
        author = re.sub(r' & ', r' \& ', reading.book.print_author)
        stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + reading.book.reftitle + ']{' + title + '}} by ' + author + ' (' + reading.book.print_year + ')\n\n')
        counter = counter + 1

    # List of rereadings
    stat_file.write('\\subsection*{List of books read more than once} \\label{sec:rereading_list}\n\n')
    counter = 1
    for book in (book for book in books if len(book.reading) > 1):
        title = re.sub(r' & ', r' \& ', book.title)
        author = re.sub(r' & ', r' \& ', book.print_author)
        stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} by ' + author + ' (' + book.print_year + ')\n\n')
        counter = counter + 1


    # Books read by year, broken down by category.
    stat_file.write('\\subsection*{Type of books read per year} \\label{sec:finished_category}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|l|l|l|l|l|l|l|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{year} & \\textit{\hyperref[category:nonfiction]{nonfiction}} & ' +
            '\\textit{\hyperref[category:collection]{collection}} & ' +
            '\\textit{\hyperref[category:novella]{novella}} & ' +
            '\\textit{\hyperref[category:shortstory]{short}} & ' +
            '\\textit{\hyperref[category:play]{play}} & ' +
            '\\textit{\hyperref[category:epicpoem]{epic}} & ' +
            '\\textit{\hyperref[category:poetry]{poetry}} & ' +
            '\\textit{\hyperref[category:graphicnovel]{graphic}} & ' +
            '\\textit{\hyperref[category:novel]{novel}} \\\\ \\hline\n')
    for x in range(num_years_read):
        if x == 0:
            stat_file.write('  Unknown')
        else:
            stat_file.write('  ' + str(min_year_read + x - 1))
        stat_file.write(' & ' + str(nonfiction_by_year[x]) + ' & ' + 
                str(collections_by_year[x]) + ' & ' + str(novellas_by_year[x]) + ' & ' + 
                str(shorts_by_year[x]) + ' & ' + str(plays_by_year[x]) + ' & ' + 
                str(epics_by_year[x]) + ' & ' + str(poetry_by_year[x]) + ' & ' + 
                str(graphic_by_year[x]) + ' & ' + str(novels_by_year[x]) + ' \\\\ \\hline\n')
    # Print totals of all years.
    stat_file.write('  total & ' + str(sum(nonfiction_by_year)) + ' & ' + 
            str(sum(collections_by_year)) + ' & ' + str(sum(novellas_by_year)) + ' & ' + 
            str(sum(shorts_by_year)) + ' & ' + str(sum(plays_by_year)) + ' & ' + 
            str(sum(epics_by_year)) + ' & ' + str(sum(poetry_by_year)) + ' & ' + 
            str(sum(graphic_by_year)) + ' & ' + str(sum(novels_by_year)) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    categories = ['Nonfiction', 'Collection', 'Novella', 'Short Story', 'Play', 'Epic Poem', 'Poetry', 'Graphic Novel', 'Novel']
    fields = ['nonfiction', 'collection', 'novella', 'shortstory', 'play', 'epicpoem', 'poetry', 'graphicnovel', 'novel']

    stat_file.write('\\subsection*{Books listed by category} \\label{sec:category_list}\n\n')
    for x in range(len(categories)):
        stat_file.write('\\subsubsection*{' + categories[x] + '} \\label{category:' + fields[x] + '}\n\n')
        counter = 1
        for book in (book for book in books if getattr(book, fields[x]) == True):
            title = re.sub(r' & ', r' \& ', book.title)
            author = re.sub(r' & ', r' \& ', book.print_author)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} by ' + author + ' (' + book.print_year + ')\n\n')
            counter = counter + 1


    # Number of books per country
    stat_file.write('\\subsection*{Books read per nation of origin of author/subject} \\label{sec:country_table}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{nation} & \\textit{count} \\\\ \\hline\n')
    for nation in sorted(countries):
#        if nation == 'USA' or nation == 'England':
#            stat_file.write('  ' + nation + ' & ' + str(countries[nation]) + ' \\\\ \\hline\n')
#        else:
            stat_file.write('  \\hyperref[nation:' + nation + ']{' + nation + '} & ' + str(countries[nation]) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    # List of books per country
    stat_file.write('\\subsection*{Books listed by nation} \\label{sec:country_list}\n\n')
    for nation in sorted(countries):
#        if nation == 'USA' or nation == 'England':
#            continue
        stat_file.write('\\subsubsection*{' + nation + '} \\label{nation:' + nation + '}\n\n')
        counter = 1
        for book in (book for book in books if book.country == nation):
            title = re.sub(r' & ', r' \& ', book.title)
            author = re.sub(r' & ', r' \& ', book.print_author)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} by ' + author + ' (' + book.print_year + ')\n\n')
            counter = counter + 1


    # Number of books per original language
    # Note: There are two reasons that the Germany + Austria + Switzerland count
    # does not equal the German-language count. First, some German-language
    # books were written by people ethnically not German (i.e. Kafka and Rilke).
    # Second, Loom of Language is English-language but written by a Swiss man.
    stat_file.write('\\subsection*{Books read per original language} \\label{sec:language_table}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{language} & \\textit{count} \\\\ \\hline\n')
    for lang in sorted(languages):
        if lang == 'English':
            stat_file.write('  ' + lang + ' & ' + str(languages[lang]) + ' \\\\ \\hline\n')
        else:
            stat_file.write('  \\hyperref[lang:' + lang + ']{' + lang + '} & ' + str(languages[lang]) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    # List of books per original language
    stat_file.write('\\subsection*{Books listed for languages other than English} \\label{sec:language_list}\n\n')
    for lang in sorted(languages):
        if lang == 'English':
            continue
        stat_file.write('\\subsubsection*{' + lang + '} \\label{lang:' + lang + '}\n\n')
        counter = 1
        for book in (book for book in books if book.language == lang):
            title = re.sub(r' & ', r' \& ', book.title)
            author = re.sub(r' & ', r' \& ', book.print_author)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} by ' + author + ' (' + book.print_year + ')\n\n')
            counter = counter + 1


    # Number of books per score
    stat_file.write('\\subsection*{Books per personal score} \\label{sec:score_table}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{score} & \\textit{count} \\\\ \\hline\n')
    for x in reversed(range(6)):
        if x == 0:
            stat_file.write('  \\hyperref[sec:score0]{Unscored')
        else:
            stat_file.write('  \\hyperref[sec:score' + str(x) + ']{' + str(x))
        stat_file.write('} & ' + str(scores[x]) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    # List of books per score
    stat_file.write('\\subsection*{Books listed by score} \\label{sec:score_list}\n\n')
    for x in reversed(range(6)):
        if x == 0:
            stat_file.write('\\subsubsection*{Unscored books} \\label{sec:score0}\n\n')
        else:
            stat_file.write('\\subsubsection*{Books given a score of ' + str(x) + '} \\label{sec:score' + str(x) + '}\n\n')
        counter = 1
        for book in (book for book in books if book.score == x):
            title = re.sub(r' & ', r' \& ', book.title)
            author = re.sub(r' & ', r' \& ', book.print_author)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} by ' + author + ' (' + book.print_year + ')\n\n')
            counter = counter + 1


    # List of series
    stat_file.write('\\subsection*{List of series} \\label{sec:series_list}\n\n')
    # Is there an easy way to ignore 'The' when sorting?
    for series in sorted(series_dict):
        stat_file.write('\\subsubsection*{' + series + '} \\label{series:' + series + '}\n\n')
        counter = 1
        series_books = sorted((book for book in books if book.series == series), key=operator.attrgetter('series_index'))
        for book in series_books:
            title = re.sub(r' & ', r' \& ', book.title)
            author = re.sub(r' & ', r' \& ', book.print_author)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} (\#' + str(book.series_index) + ') by ' + author + ' (' + book.print_year + ')\n\n')
            counter = counter + 1


    # Most read authors
    stat_file.write('\\subsection*{Most read authors} \\label{sec:author_table}\n\n')
    stat_file.write('\\begin{tabular}{|r|l|}\n')
    stat_file.write('  \\hline\n')
    stat_file.write('  \\textit{author} & \\textit{count} \\\\ \\hline\n')
    for author in sorted(authors, key=lambda x:len(x.books), reverse=True):
        # Only list authors with more than two books read. This is more or less
        # to prevent a table that is larger than one page. If it is ever
        # desirable to have a multi-page table, look into the longtable or xtab
        # packages.
        if len(author.books) > 2:
            stat_file.write('  \\hyperref[sec:' + author.label_name + ']{' + author.print_name + '} & ' + str(len(author.books)) + ' \\\\ \\hline\n')
    stat_file.write('\\end{tabular}\n')

    # List of books by author (sorted by publication year)
    stat_file.write('\\subsection*{Books listed by author} \\label{sec:author_list}\n\n')
    for author in sorted(authors, key=operator.attrgetter('sort_name')):
        stat_file.write('\\subsubsection*{' + author.print_name + '} \\label{sec:' + author.label_name + '}\n\n')
        counter = 1
        for book in sorted(author.books, key=lambda x:x.year):
            title = re.sub(r' & ', r' \& ', book.title)
            stat_file.write(str(counter) + '. \\textit{\\hyperref[sec:' + book.reftitle + ']{' + title + '}} (' + book.print_year + ')\n\n')
            counter = counter + 1


    # List of books by length of time spent reading them
    stat_file.write('\\subsection*{Books listed by duration} \\label{sec:duration_list}\n\n')
    for reading in sorted(readings, key=operator.attrgetter('duration')):
        if reading.unknown or reading.unfinished or reading.date_strs[0] == 0:
            continue
        title = re.sub(r' & ', r' \& ', reading.book.title)
        author = re.sub(r' & ', r' \& ', reading.book.print_author)
        stat_file.write('\\textit{\\hyperref[sec:' + reading.book.reftitle + ']{' + title + '}} by ' + author + ' (' + reading.book.print_year + '): ' + str(reading.duration.days + 1))
        if reading.duration.days == 0: # 1 day
            stat_file.write(' day\n\n')
        else:
            stat_file.write(' days\n\n')

    # Calculate most number of books in progress at one time? Tedious!


def parse_authors(authors, author_sort, author_print):
    # Parse the author strings and add to the author list if not there.
    # Returns the individual authors.
    
    # Expect each author (in both _sort and _print) to be separated by a single
    # ampersand (and spaces). An escape character (\) is unnecessary. Split
    # based on the &.
    
    authors_sort = author_sort.split('&')
    authors_print = author_print.split('&')
    # Remove leading and trailing whitespace from each author name.
    authors_sort = [x.strip(' ') for x in authors_sort]
    authors_print = [x.strip(' ') for x in authors_print]
    book_authors = [];

    # Check if the sort version is already in the authors list. If not, create
    # it and add it. Compare author.label_name and authors_sort since neither
    # have been flipped for sorting (yet).
    for i in range(len(authors_sort)):
        found = False
        for author in authors:
            if author.label_name == authors_sort[i]:
                book_authors.append(author)
                found = True
                break
        if not found:
            # New author.
            new_author = Author(authors_sort[i], authors_print[i])
            authors.append(new_author)
            book_authors.append(new_author)

    return book_authors


def fix_special_characters(line):
    # Agape Agape and Kobo Abe are messed up because of the braces use in LaTeX
    # to represent the special characters in those names. If possible, convert
    # them to the proper Unicode representation. For older Pythons, just remove
    # the accent marks.
    if sys.version_info >= (3, 0):
        line = re.sub(r'\\=\{(e)\}', u'\u0113', line)
        line = re.sub(r'\\=\{(o)\}', u'\u014D', line)
    else:
        line = re.sub(r'\\=\{([aeiou])\}', r'\1', line)
    return line


if __name__ == '__main__':
    main()
