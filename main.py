import discord
from discord.ext import tasks
import os
from datetime import datetime, timezone
from dateutil import parser
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

sent_message = False

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

google_calendar_token = os.getenv('GOOGLE_CALENDAR_TOKEN')


@client.event
async def on_ready():
    logging.info(f'{client.user} has connected to Discord!')
    print(f'{client.user} has connected to Discord!')
    sent_message_resetter.start()
    upcoming_events.start()


def google_calendar_events():
    """
    Fetches upcoming events from Google Calendar and returns them as a list.
    Returns:
      A list of dictionaries, where each dictionary represents an event with the following keys:
        - 'start': The start time of the event (in RFC 3339 format).
        - 'summary': The title of the event.
    """
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("User login required. Please implement a login flow.")
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = events_result.get("items", [])
        if not events:
            return []
        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_list.append({"start": start, "summary": event["summary"]})
        return event_list
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return []


@tasks.loop(minutes=5)
async def upcoming_events():
    global sent_message
    try:
        event_list = google_calendar_events()
        logging.info(event_list)
        logging.info(datetime.now(pytz.utc))
        if not event_list:
            logging.info("No upcoming events found.")
            return
        event_message = ""
        for event in event_list:
            start_time_str = event["start"]
            start_time = parser.parse(start_time_str)
            current_time = datetime.now(start_time.tzinfo)
            unix_timestamp = int(start_time.timestamp())
            time_diff = start_time - current_time
            if 0 <= time_diff.total_seconds() <= 1800:
                summary = event["summary"]
                event_message += f"<t:{unix_timestamp}:R> - {summary}\n"
        if event_message and not sent_message:
            channel = client.get_channel(os.getenv("CHANNEL_ID"))
            await channel.send(f"Upcoming events @everyone:\n{event_message}")
            sent_message = True
            logging.info(event_message)
        else:
            logging.info("No upcoming events within the next 30 minutes.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


@tasks.loop(minutes=30)
async def sent_message_resetter():
    global sent_message
    sent_message = False
    logging.info("Sent message reset")


client.run(os.getenv("DISCORD_TOKEN"))
