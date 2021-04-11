# load discord bot
import os
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# get upcoming events
from googleCalendarApi import fetchUpcomingEvents

# datetime to calculate times
from datetime import datetime
from dateutil.parser import parse
from dateutil.tz import gettz, UTC

# async sleep
import asyncio



#initialize
events = {}     # events dict with all upcoming events
reminders = []  # reminderslist of all eventKeys with reminders on the way
tMinus = 45      # Reminder time in minutes before the start of the meeting
channels = {}   # dict of channels to message




# helperfunctions
def embedFactory(eventKey, timesIncluded = True, footerIncluded = True):
    # create an appealing calendar item overview as embed for discord
    # only append specific starttimes in advance. At start of the event this function is called without t & startUTC.
    
    # eventKey is a unique generated key for the events dict (generated in getCal() 1. )
    
    # t = timeNow, startUTC = startUTC | Both in datetime format 
    
    if events[eventKey]['description'] is not None:
        embedVar=discord.Embed(title=events[eventKey]['subject'], description=events[eventKey]['description'], color=0xf570ff)
    else:
        embedVar=discord.Embed(title=events[eventKey]['subject'], description="*No description available*", color=0xf570ff)
        
    if footerIncluded:    
        embedVar.set_footer(text="Would you like to participate in our ecosystem? Come join one of the weekly committee meetings!")
    
    if timesIncluded: # calculate startTimes
    
        # start in utc-5(EST)        
        start = parse(events[eventKey]['startUTC-5'])
        
        # convert times
        startUTC = start.replace(tzinfo=UTC) - start.utcoffset()
    
        # create the embed
        embedVar.add_field(name="Start time in GMT/UTC",  value=startUTC.strftime("%H:%M"), inline=False)
        embedVar.add_field(name="New York", value=startUTC.astimezone(gettz('America/New_York')).strftime("%H:%M"), inline=True)
        embedVar.add_field(name="London",   value=startUTC.astimezone(gettz('Europe/London')).strftime("%H:%M"), inline=True)
        embedVar.add_field(name="Bangkok",  value=startUTC.astimezone(gettz('Asia/Bangkok')).strftime("%H:%M"), inline=True)
    
    return embedVar






async def scheduleReminders(eventKey, secondsTillEvent):
    # schedules a reminder at tMinus & 0 minutes before event meeting.
    
    # eventKey is a unique generated key for the events dict (generated in getCal() 1. )
    # secondsTillEvent is the time from now till the eventstart 
    
    # add the eventKey to the reminders list while this function is running
    reminders.append(eventKey)
    
    # format the time until the next event
        # hours, remainder = divmod(secondsTillEvent, 3600)
        # minutes, seconds = divmod(remainder, 60)
        # sformat = '{:02}h {:02}m'.format(int(hours), int(minutes))
    
    timeTillFirstReminder = secondsTillEvent - (60*tMinus)

    # grab the correct committee channel from the classification
    try:
        committeeChannel = channels[ events[eventKey]['classification'] ] #query the channels dict with the classification
    except:
        print("Couldnt find correct committeeChannel for: "+eventKey)
        committeeChannel = False #only sends messages to the general channel
        
    if timeTillFirstReminder > 0: #only notify at tMinus if thats in the future
    
        # sleep till tMinus
        await asyncio.sleep(timeTillFirstReminder)            
        
        # remind at tMinus
        embed = embedFactory(eventKey)
        await channels['general'].send(events[eventKey]['subject']+" starts in "+str(tMinus)+" minutes!", embed=embed)
        await channels['telegram-bridge'].send(events[eventKey]['subject']+" starts in "+str(tMinus)+" minutes in the Discord meeting room!")
        if committeeChannel:
            await committeeChannel.send(events[eventKey]['subject']+" starts in "+str(tMinus)+" minutes!", embed=embed)
            
        # sleep till meeting start
        await asyncio.sleep(tMinus*60)
        
    else: #event is in the future but tMinus is already past
        await asyncio.sleep(secondsTillEvent)   # sleep untill start reminder
        
        
    # remind at event start
    
    # check if event has not been deleted since the start of this function at tMinus:
    if eventKey in events:
    
        embedNoTimes = embedFactory(eventKey, False, False)
        # if committeeChannel:
            # await committeeChannel.send(events[eventKey]['subject']+" starts now!", embed=embedNoTimes)
        await channels['general'].send(events[eventKey]['subject']+" starts now!", embed=embedNoTimes)
        await channels['events'].send(events[eventKey]['subject']+" starts now!", embed=embedNoTimes)
        await channels['telegram-bridge'].send(events[eventKey]['subject']+" starts now in the Discord meeting room!")
    
    
    # remove the event from the reminder list
    if eventKey in reminders:
        reminders.remove(eventKey)

    
# connect bot client
client = discord.Client()

# BOT MAIN CODE
@client.event
async def on_ready():
    print("Bot: secretMeetingAnnouncer connected")
    getCal.start()      

         
@tasks.loop(hours=1)
async def getCal():
    global events # assign the events to the global variable

    #import google calendar
    try:
        importedEvents = fetchUpcomingEvents()
    except:
        print("Error: couldn't get the upcoming events from the google calendar.")
    
    # calculate time now
    now = datetime.now(UTC)  
    
 
    # 1. populate the events variable with new or updated events

    if 'importedEvents' in locals(): #check if importedEvents is loaded correctly in memory

        # Check to see if importedEvents[] is not empty
        if len(importedEvents)>0:
        
            for event in importedEvents:
        
                eventKey = event['startUTC-5']+'_'+event['subject'] # generate unique dict key
                events[eventKey] = event
    
    else: # no upcoming events
        print("Could not find any upcoming events!")
        
        
    # 2. delete the events that are no longer present in the last imported events from gcal but are still in the events variable
    events = {key:event for key, event in events.items() if event in importedEvents}  
    
    
    
    # 3. schedule the reminders (only if it should appear before the next loop iteration)

    if bool(events): #check if events is not empty
    
        # loop all over the upcoming events to find out which events lie between now (latest gCal refresh) and the next gCal refresh (in 1hr)
        for eventKey, event in events.items():
        
            # in case the reminders are already scheduled skip to the next event
            if eventKey in reminders: 
                continue
        
            # datetime (t) straight from g calendar in utc-5(EST)        
            t = parse(event['startUTC-5'])
            
            # convert to UTC
            startUTC = t.replace(tzinfo=UTC) - t.utcoffset()
                                
            # time till event
            d = startUTC-now
            s = d.total_seconds()
                        
            # # if time till next meeting is less than 1hr (the next cal update) + tMinus, schedule the reminder(s) 
            if s < ((1*60*60)+(tMinus*60)) and s>0:
                print("Sending reminders for: "+eventKey+" ...")

                # loop instead of wait to run scheduleReminders in parallel 
                loop = asyncio.get_event_loop()
                loop.create_task(scheduleReminders(eventKey, s))
        
@getCal.before_loop
async def getCal_before():
    try: 
        channels['general']     = client.get_channel(360051864110235649)
        channels['Awareness']   = client.get_channel(760897115466498089)
        channels['Development'] = client.get_channel(760897182756503572)
        channels['Governance']  = client.get_channel(682254187027103781)
        channels['Education']   = client.get_channel(760897254613057667)
        channels['Analytics']   = client.get_channel(764166414289993838)
        channels['Website']     = client.get_channel(766758769191026688)
        channels['Design']      = client.get_channel(764232860906684446)
        channels['Infrastructure'] = client.get_channel(760897475514204160)
        channels['Biz Dev']     = client.get_channel(826501840757194773)
        channels['telegram-bridge']     = client.get_channel(761654190631288893)
        channels['events']     = client.get_channel(822489737154658359)
    except:
        print("couldn't load the correct channels")

        
# run bot
client.run(TOKEN)