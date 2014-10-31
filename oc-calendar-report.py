#!/usr/bin/python
# Read the OwnCloud database, produce html report of events in next week
# I use the following command in a cron job to send it:
# Example use: 
#   python owncloud_reminder.py  | mail -a 'Content-Type: text/html; charset=iso-8859-1' -s "Events in next 7 days" username@email.com

import sqlite3
import vobject
import datetime
import time
from datetime import date
from dateutil.rrule import *
from dateutil import tz

# Connect to database
con = sqlite3.connect('/var/www/owncloud/data/owncloud.db')
cur = con.cursor()

# Get List of calendar names for user
cur.execute('SELECT userid,displayname,id FROM oc_clndr_calendars')
ca = []
while 1:
  data = cur.fetchone()
  if data==None:
    break
  ca.append( data[1] )

# Get Target range as datetime
curdt = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
enddt = curdt  + datetime.timedelta(days=7)
#print(datetime.datetime.now())

# Get all calender event objects
cur.execute("SELECT calendardata,calendarid FROM oc_clndr_objects")

# Get list of events in upcoming week
# We have to go through all the events because they may have a repeating rule that generates an instance within the week in question
# (Strictly, we don't need to look at events that start after the week - not coded)
week=[]
while 1:
  data = cur.fetchone()
  if data==None:
    break
    
  #Parse the VCALENDAR object, get the VEVENT
  a = vobject.readComponents(data[0]).next()
  #a.prettyPrint()

  #we want the event start as a date and as a datetime
  #some events are dates, and some are times, either way we want both:
  #we want all datetimes in local time, some will need converting

  if hasattr(a.vevent.dtstart.value,"tzinfo"):
    if a.vevent.dtstart.value.tzinfo != None:
      # we have a datetime already and we have tzinfo, convert to local time
      dtstart = a.vevent.dtstart.value.astimezone(tz.tzlocal())
      dtstart = dtstart.replace(tzinfo=None)
      dstart = dtstart.date()
    else:
      # we have a datetime, remove timezone info
      dtstart = a.vevent.dtstart.value.replace(tzinfo=None)
      dstart = dtstart.date()
  else:
    # a date, convert to a datetime
    dstart = a.vevent.dtstart.value
    dtstart = datetime.datetime.combine(a.vevent.dtstart.value, datetime.datetime.min.time())


  if hasattr(a.vevent, "rrule"):
    # a repeating event - check expansion of rule against date range
    re = rrulestr(a.vevent.rrule.value,dtstart=dtstart )
    rea=list(re.between(curdt,enddt,inc=True))
    for p in rea:
      # append orginal datetime time of day to rrule day (we will sort on it)
      p = datetime.datetime.combine(p, dtstart.time())
      # add to week list
      week.append([p,a.vevent.summary.value, ca[ data[1]-1 ], a ])
  else:
    if dstart >= curdt.date() and dstart <= enddt.date():
      # add 0 hrs 0mins to date to get datetime (we will sort on it)
      dtstart = datetime.datetime.combine(dtstart, datetime.datetime.min.time())
      # add to week list
      week.append([dtstart,a.vevent.summary.value, ca[ data[1]-1 ] ])

# sort them
week.sort( key=lambda a:a[0] )

print("<html>")

print("<h1>Events Today: "+curdt.strftime("%A %B %d %Y")+"</h1>")
print("<table>")
found = False
for d in week:
  if (d[0].date() == curdt.date()):
    found = True
    print("<tr>")
    print("<td>"+d[0].strftime("%a %B %d")+"<td style='min-width:100px;'>"+d[1]+"<td>"+d[0].strftime("%I:%M:%S %p")+"<td>"+d[2]+"")
if found == False:
  print("<tr><td>No Events Today")
print("</table>")

print("<hr>")

print("<h1>Coming up:</h1>")
print("<table>")
found = False
for d in week:
  #d[3].prettyPrint()
  if (d[0].date() != curdt.date()):
    found = True
    print("<tr>")
    print("<td>"+d[0].strftime("%a %B %d")+"<td style='min-width:100px;'>"+d[1]+"<td>"+d[0].strftime("%I:%M:%S %p")+"<td>"+d[2]+"")
if found == False:
  print("<tr><td>No Events In Next 7 days")
print("</table>")

print("</html>")


