from __future__ import print_function
import datetime
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from bs4 import BeautifulSoup  # parse some tags

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def fetchUpcomingEvents():
    """Fetches the upcoming 10 events on the public secret network calendar

    Returns a list of events with startdateTime, enddateTime, subject and description
    """

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API and populate var events
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    # print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='b1cv985ld9h0qdcgb02a795el4@group.calendar.google.com', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    # parse events for returning the required event list
    if not events:
        print('No upcoming events found.')

    result = []

    for event in events:
        cleanEvent = {}

        # check if it's a public event (summary is not available for private events)
        if ('summary' not in event) or ('visibility' == 'private'):
            continue

        # clean the input
        cleanEvent['startUTC-5'] = event['start'].get('dateTime')
        cleanEvent['endUTC-5'] = event['end'].get('dateTime')
        cleanEvent['subject'] = event.get('summary')
        cleanEvent['description'] = parseDescr(event.get('description'))

        # add classification
        if "Awareness" in cleanEvent['subject']:
            cleanEvent['classification'] = "Awareness"
        elif "Development" in cleanEvent['subject']:
            cleanEvent['classification'] = "Development"
        elif "Governance" in cleanEvent['subject']:
            cleanEvent['classification'] = "Governance"
        elif "Education" in cleanEvent['subject']:
            cleanEvent['classification'] = "Education"
        elif "Analytics" in cleanEvent['subject']:
            cleanEvent['classification'] = "Analytics"
        elif "Website" in cleanEvent['subject']:
            cleanEvent['classification'] = "Website"
        elif "Design" in cleanEvent['subject']:
            cleanEvent['classification'] = "Design"
        elif "Infrastructure" in cleanEvent['subject']:
            cleanEvent['classification'] = "Infrastructure"
        elif "Biz Dev" in cleanEvent['subject']:
            cleanEvent['classification'] = "Biz Dev"
        else:
            cleanEvent['classification'] = "Other"

        # append to the resulting list
        result.append(cleanEvent)

    return result


def parseDescr(text):
    # replace breaktags with newlines
    text = text.replace('<br>', '\n')

    # replace non breakings spaces
    text = text.replace('&nbsp;', ' ')

    # replace any possible html link tags
    soup = BeautifulSoup(text)

    if soup.p.a != None:
        href = soup.p.a['href']
        linktext = soup.p.a.text

        soup.p.a.replace_with('[{}]({})'.format(linktext, href))

    return soup.p.text


if __name__ == '__main__':
    fetchUpcomingEvents()
