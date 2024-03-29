#!/usr/bin/env python3
# File: mbta2rss
# Description: This pulls down all queried MBTA alerts and prints them out.
# Author: Ben O'Neill <ben@benoneill.xyz>
# Copyright: Copyright (C) 2019-2021 Ben O'Neill <benoneill.xyz>. Licensed under
# the GNU GPL v3.

import argparse, os, requests, html
from datetime import datetime

API_URL = 'https://api-v3.mbta.com/'
API_KEY = ''
DEFAULT_TITLE = 'Unofficial MBTA Alert Feed'
DEFAULT_DESC = 'An unofficial feed for public transit alerts in the Boston area.'
DEFAULT_LANG = 'en_us'
DEFAULT_URL = 'https://github.com/darklands1/mbta-rss'
DEFAULT_DATATYPE = 'alerts'

"""
Driver for printing Markdown alert output. This formats the data from the API
to be semi-neatly displayed in basic Markdown
"""
class MarkdownAlertDriver:
    def __init__(self, title=DEFAULT_TITLE, desc=DEFAULT_DESC,
            lang=DEFAULT_LANG, url=DEFAULT_URL):
        self.title = title
        self.desc = desc
        self.lang = lang
        self.url = url
    
    """ Stuff to print before the main content """
    def print_start(self):
        print('# ' + title)
        print(desc)

    """ Format and print alert """
    def print_item(self, header, long_header='', desc='', effect='', date='', categories=[], guid=''):
        print('## ' + header + ' (added ' + date + ')')
        print(long_header + '\n\n' + desc.replace('\n', '\n\n') + '\n\n')

    """ Stuff to print after the main content (empty in this case but defined for consistency) """
    def print_end(self):
        pass

"""
Driver for printing RSS alert output. This formats the data from the API
to be semi-neatly displayed as an RSS feed.
"""
class RSSAlertDriver:
    def __init__(self, title=DEFAULT_TITLE, desc=DEFAULT_DESC,
            lang=DEFAULT_LANG, url=DEFAULT_URL):
        self.title = title
        self.desc = desc
        self.lang = lang
        self.url = url
    
    """ Stuff to print before the main content """
    def print_start(self):
        print('<?xml version="1.0" encoding="utf-8"?>')
        print('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
        print('<channel>')
        print('<title>' + self.title + '</title>')
        print('<description>' + self.desc + '</description>')
        print('<language>' + self.lang + '</language>')
        print('<link>' + self.url + '</link>')

    """ Format and print alert """
    def print_item(self, header, long_header='', desc='', effect='', date='',
            categories=[], guid=''):
        content = "<pre>" + html.escape(long_header) + "\n\n" + html.escape(desc) + "</pre>"

        print('<item>')
        print('<title>' + html.escape(header) + '</title>')
        print('<description>' + content + '</description>')
        print('<pubDate>' + date + '</pubDate>')
        print('<guid>' + guid + '</guid>')
        for category in categories:
            print('<category>' + category + '</category>')
        print('</item>')

    """ Stuff to print after the main content """
    def print_end(self):
        print('</channel>')
        print('</rss>')

""" Sends a request to the API and return the JSON output """
def retrieve_from_api(req):
    return requests.get('https://api-v3.mbta.com/' + req).json()

""" Facilitates conversion of alerts from the JSON API into the desired format. """
def get_alerts(driver, route, time):
    driver.print_start()

    req_str = 'alerts'
    character = '?'

    if time != None:
        # only list alerts in effect at a given time
        req_str += character + 'filter[datetime]=' + time
        character = '&'
    if API_KEY != None:
        # use an API key for more requests per minute
        req_str += character + 'api_key=' + API_KEY
        character = '&'
    if route != None:
        # filter to certain routes
        req_str += character + 'filter[route]=' + route
        character = '&'

    # retrieve API result using the formatted request
    alerts = retrieve_from_api(req_str)

    for alert in alerts['data']:
        attributes = alert['attributes']
        desc = ''
        effect = ''
        categories = [] # TODO currently unused, how to implement?
        guid = alert['id']

        header = attributes['short_header'] # this should always be non-empty
        long_header = attributes['header'] # this should always be non-empty
        dt = datetime.fromisoformat(attributes['created_at'])
        date = dt.strftime('%m-%d-%Y %I:%M %p')

        if attributes['description'] != None:
            desc = attributes['description']

        if attributes['effect'] != None:
            effect = 'Effect: ' + attributes['effect']

        # print using given driver
        driver.print_item(header, long_header, desc, effect, date, categories, guid)

    driver.print_end()

"""
List stops for each route in a list (only works for Markdown, output
is hardcoded in that format currently).
"""
def get_stoplist(routes):
    if routes == None:
        print("route list must be provided when listing stops")
        exit(1)

    driver.print_start()
    for route in routes.split(','):
        reqstr = 'stops?filter[route]=' + route
        if API_KEY != None:
            reqstr += '&api_key=' + API_KEY
        stoplist = retrieve_from_api(reqstr)
        print("## Route: " + route)
        for stop in stoplist['data']:
            print("* " + stop['attributes']['name'])
    driver.print_end()

if __name__ == '__main__':
    # Set defaults
    title = DEFAULT_TITLE
    desc = DEFAULT_DESC
    url = DEFAULT_URL
    datatype = DEFAULT_DATATYPE
    driver = None

    # Add potential arguments to parser
    parser = argparse.ArgumentParser(description='Pull down MBTA alerts and print them out')
    parser.add_argument('-d', '--datatype', help="data to grab", metavar='DATATYPE')
    parser.add_argument('-o', '--output', help='set output format', metavar='OUTFMT')
    parser.add_argument('-r', '--routes', help='set route list', metavar='ROUTELIST')
    parser.add_argument('-t', '--time', help='set time to check alerts for', metavar='TIME')
    parser.add_argument('-T', '--title', help='set output title', metavar='TITLE')
    parser.add_argument('-D', '--description', help='set output description', metavar='DESC')
    parser.add_argument('-U', '--url', help='set upstream URL', metavar='URL')

    # Parse arguments
    args = parser.parse_args()
    outfmt = args.output
    routes = args.routes
    time = args.time
    if args.title != None:
        title = args.title
    if args.description != None:
        desc = args.description
    if args.url != None:
        url = args.url
    if args.datatype != None:
        datatype = args.datatype

    # Get the API key. We are using an environment variable for better
    # security. It's fine if this is empty/undefined as long as API
    # calls are limited in frequency.
    API_KEY = os.getenv("API_KEY")

    # Check for output driver
    if outfmt == None or outfmt == 'rss':
        driver = RSSAlertDriver(title, desc, DEFAULT_LANG, url)
    elif outfmt == 'md':
        driver = MarkdownAlertDriver(title, desc, DEFAULT_LANG, url)
    else:
        print("No such output driver.")
        exit(0)

    # Execute desired tool/function
    if datatype == 'alerts':
        get_alerts(driver, routes, time)
    elif datatype == 'stops':
        get_stoplist(routes)
    else:
        print("No such data type.")
        exit(0)
