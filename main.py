import threading
import discord
import os
import asyncio
import time
from datetime import datetime, timezone
from dateutil import parser
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import logging
from fastapi import FastAPI
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

sent_message = False

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

app = FastAPI()

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

TOKEN = os.getenv("TOKEN")


@app.on_event("startup")
async def startup_event():
    logging.info("Starting up bot")
    asyncio.create_task(bot.start(TOKEN))
    await asyncio.sleep(5)
    print(f"{bot.user} has connected to Discord!")
    bot.loop.create_task(scheduled_upcoming_events())


def google_calendar_events():
    """
    Fetches upcoming events from Google Calendar and returns them as a list.
    Returns:
      A list of dictionaries, where each dictionary represents an event with the following keys:
        - 'start': The start time of the event (in RFC 3339 format).
        - 'summary': The title of the event.
    """
    creds = None
    if os.path.exists("token.json"):
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
            calendarId="d4528073bf6b10d751df59727be5733d1f31beea44b0f03e1a60087e46dd7a19@group.calendar.google.com",
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
            channel = bot.get_channel(1253856173929529426)
            await channel.send(f"Upcoming events @everyone:\n{event_message}")
            sent_message = True
            logging.info(event_message)
        else:
            logging.info("No upcoming events within the next 30 minutes.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


def sent_message_resetter():
    global sent_message
    sent_message = False
    logging.info("Sent message reset")


async def scheduled_upcoming_events():
    while True:
        await upcoming_events()
        await asyncio.sleep(1800)


def scheduled_sent_message_resetter():
    while True:
        sent_message_resetter()
        time.sleep(25200)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/events/get")
async def google_events_get():
    event_list = google_calendar_events()
    return event_list

@app.get("/bot/sendmessage/{message}")
async def send_message(message: str):
    channel = bot.get_channel(1253856173929529426)
    await channel.send(message)
    return {"message": "Message sent!"}



thread = threading.Thread(target=scheduled_sent_message_resetter)
thread.start()

if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=5000)
