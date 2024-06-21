import discord
import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def google_calendar_events():
  """
  Fetches upcoming events from Google Calendar and returns them as a list.

  Returns:
    A list of dictionaries, where each dictionary represents an event with the following keys:
      - 'start': The start time of the event (in RFC 3339 format).
      - 'summary': The title of the event.
  """

  creds = None
  # Check for existing token file
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

  # If credentials are missing or expired, attempt refresh or user login
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      # Implement user login flow (outside the scope of this example)
      # You'll need to use a library like Google Auth for Python
      raise RuntimeError("User login required. Please implement a login flow.")

  try:
    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + "Z"
    events_result = (
        service.events()
        .list(
            calendarId="d4528073bf6b10d751df59727be5733d1f31beea44b0f03e1a60087e46dd7a19@group.calendar.google.com",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      return []  # Return empty list if no upcoming events

    # Build the list of event dictionaries
    event_list = []
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))
      event_list.append({"start": start, "summary": event["summary"]})

    return event_list

  except HttpError as error:
    print(f"An error occurred: {error}")
    return []  # Return empty list on error

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

tree = discord.app_commands.CommandTree(client)

"--> Bot says its own name"
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=731863372563349627))
    print(f'We have logged in as {client.user}')
    
# make the slash command
@tree.command(
    name="upcomingevents",
    description="Upcoming Arbeit Events",
    guild=discord.Object(id=731863372563349627)
)
async def upcoming_events(interaction):
    try:
        event_list = google_calendar_events()

        if not event_list:
            await interaction.response.send_message("No upcoming events found.")
            return

        # Process and format the event list for a Discord message
        event_message = ""
        for event in event_list:
            start_time = event["start"]  # Assuming it's in RFC 3339 format
            summary = event["summary"]
            event_message += f"{start_time} - {summary}\n"

        await interaction.response.send_message(event_message)
    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.response.send_message("An error occurred while fetching events. Please try again later.")
    
client.run(os.getenv('TOKEN'))


