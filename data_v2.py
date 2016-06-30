

#import requests
import json
import datetime
import pytz
import time
from collections import Counter
import dateutil.parser
from simple_salesforce import Salesforce

sf = Salesforce(
    username='integration@levelsolar.com',
    password='HrNt7DrqaEfZmBqJRan9dKFzmQFp',
    security_token='yWlJG8lAKCq1pTBkbBMSVcKg')

# define employee roles for set source
event_reps = ['a023900000SzCo3AAF', 'a023900000UjVT4AAN', 'a023900000UjFJGAA3', 'a023900000Trg9TAAR', 'a027000000Pue1UAAR', 'a023900000UbHglAAF', 'a023900000UbHgbAAF',
              'a023900000TflZvAAJ', 'a023900000UabRbAAJ', 'a027000000QsCBXAA3', 'a027000000R78PGAAZ', 'a023900000UilrLAAR', 'a023900000UilrQAAR', 'a023900000UilrVAAR',
              'a023900000UilrfAAB', 'a023900000UilzPAAR', 'a023900000SSclmAAD', 'a023900000SSclhAAD', 'a023900000SSclcAAD', 'a023900000UjytLAAR', 'a027000000RIuroAAD',
              'a027000000RIuryAAD', 'a027000000RIurUAAT', 'a027000000RIurtAAD', 'a023900000UPD2tAAH', 'a023900000UPD2yAAH', 'a023900000UPD33AAH', 'a023900000UQkYOAA1',
              'a023900000UOxIPAA1']

# time definitions
one_day = datetime.timedelta(days=1)
utc_zone = pytz.timezone('UTC')
est_zone = pytz.timezone('US/Eastern')
now_utc_naive = datetime.datetime.utcnow()
now_utc_aware = utc_zone.localize(now_utc_naive)
now_est_aware = now_utc_aware.astimezone(est_zone)
today_12am_est = now_est_aware.replace(hour=0, minute=0, second=0)

# fetch data from Salesforce
metrics_today = sf.apexecute('metricsdashboard?period=TODAY')
metrics_tw = sf.apexecute('metricsdashboard?period=THIS_WEEK')
sets_today = sf.query("select scheduleddate__c, lead__r.county__c, lead__r.LASERCA__Home_State__c, lead__r.ambassador__c, lead__r.hq_rep__c, lead__r.lead_source_hierarchy__c from interaction__c where createddate = today and subject__c = 'Closer Appointment' and lead__c != null")["records"]
appts_tmrw = sf.query("select scheduleddate__c, lead__r.county__c, lead__r.LASERCA__Home_State__c, lead__r.ambassador__c, lead__r.hq_rep__c, lead__r.lead_source_hierarchy__c from interaction__c where scheduleddate__c = tomorrow and subject__c = 'Closer Appointment' and canceled__c = false and lead__c != null")["records"]
cads_tmrw = sf.query("select scheduleddate__c, lead__r.county__c, lead__r.LASERCA__Home_State__c, lead__r.ambassador__c, lead__r.hq_rep__c, lead__r.lead_source_hierarchy__c from interaction__c where scheduleddate__c = tomorrow and subject__c = 'CAD Appointment' and canceled__c = false and contact__c != null")["records"]
outcomes = sf.query("select outcome__c from interaction__c where interactiondate__c = today and subject__c = 'CAD Appointment'")["records"]

# key totals
sales_today = metrics_today["Sales"]
g2g_today = metrics_today["G2G"]
permits_today = metrics_today["Permits"]
sales_tw = metrics_tw["Sales"]
g2g_tw = metrics_tw["G2G"]
permits_tw = metrics_tw["Permits"]
total_cads_tmrw = len(cads_tmrw)
potential_sits = metrics_today["PotentialSits"]
sits = metrics_today["Sits"]
cad_outcomes = len(outcomes)
nmt = 0
cancels = 0
total_sets_today = len(sets_today)

for outcome in outcomes:
	if outcome["Outcome__c"] == "NMT - Have All Docs" or outcome["Outcome__c"] == "NMT - Need Some Docs":
		nmt += 1
	if outcome["Outcome__c"] == "Wants to cancel":
		cancels += 1

# rates
if potential_sits == 0:
	sit_rate = "0%"
elif sits > potential_sits:
	sit_rate = "100%"
else:
	sit_rate = "{0:.0f}%".format((float(sits)/float(potential_sits))*100)

if cad_outcomes == 0:
	g2g_rate = "0%"
elif g2g_today > cad_outcomes:
	g2g_rate = "100%"
else:
	g2g_rate = "{0:.0f}%".format((float(g2g_today)/float(cad_outcomes))*100)

if sits == 0:
	close_rate == "0%"
elif sales_today > sits:
	close_rate = "100%"
else:
	close_rate = "{0:.0f}%".format((float(sales_today)/float(sits))*100)

# build dictionaries
markets = ["Suffolk", "Nassau", "Richmond", "Queens", "Kings", "Mass"]
sources = {"field": 0, "isr": 0, "events": 0, "partners": 0, "total": 0}
sales_tmrw = {}
set_details = {}
for market in markets:
	sales_tmrw[market] = 0
	sales_tmrw["total"] = 0
	set_details[market] = {}
	for key in sources:
		set_details[market][key] = 0

# define function for sourcing set
def source_appt(appt):
	source = "field"
	if appt["Lead__r"]["Lead_Source_Hierarchy__c"]:
		if "Partner" in appt["Lead__r"]["Lead_Source_Hierarchy__c"]:
			source = "partners"
		elif appt["Lead__r"]["HQ_Rep__c"]:
			source = "isr"
		elif appt["Lead__r"]["Ambassador__c"]:
			if appt["Lead__r"]["Ambassador__c"] in event_reps:
				source = "events"
	elif appt["Lead__r"]["HQ_Rep__c"]:
		source = "isr"
	elif appt["Lead__r"]["Ambassador__c"]:
		if appt["Lead__r"]["Ambassador__c"] in event_reps:
			source = "events"
	return source

# fill dictionary for sets by market and source, as well as source totals
def fill_set_details():
	for appt in sets_today:
		if appt["Lead__r"]["LASERCA__Home_State__c"]:
			if appt["Lead__r"]["LASERCA__Home_State__c"] == "MA":
				source = source_appt(appt)
				set_details["Mass"]["total"] += 1
				set_details["Mass"][source] += 1
				sources[source] += 1
			elif appt["Lead__r"]["county__c"]:
				if appt["Lead__r"]["county__c"].title() in markets:
					source = source_appt(appt)
					market = appt["Lead__r"]["county__c"].title()
					set_details[market]["total"] += 1
					set_details[market][source] += 1
					sources[source] += 1

# define function for distribution of sets by scheduled days in the future
def set_distribution():
	global distribution
	distribution = {"0": 0, "1": 0, "2": 0, "3-4": 0, "5-7": 0, "8+": 0}
	for appt in sets_today:
		if appt["ScheduledDate__c"]:
			days_out = (dateutil.parser.parse(appt["ScheduledDate__c"]).astimezone(est_zone) - today_12am_est).days
			if days_out == 0:
				if dateutil.parser.parse(appt["ScheduledDate__c"]).astimezone(est_zone).day == today_12am_est.day:
					days_out = 0
				else:
					days_out = 1
			if days_out == 0:
				distribution["0"] += 1
			elif days_out == 1:
				distribution["1"] += 1
			elif days_out == 2:
				distribution["2"] += 1
			elif days_out >= 3 and days_out <=4:
				distribution["3-4"] += 1
			elif days_out >= 5 and days_out <=7:
				distribution["5-7"] += 1
			elif days_out >= 8:
				distribution["8+"] += 1

# sales appointments tomorrow
def sales_appts_tmrw():
	for appt in appts_tmrw:
		if appt["Lead__r"]["LASERCA__Home_State__c"]:
			if appt["Lead__r"]["LASERCA__Home_State__c"] == "MA":
				sales_tmrw["Mass"] += 1
				sales_tmrw["total"] += 1
			elif appt["Lead__r"]["county__c"]:
				if appt["Lead__r"]["county__c"].title() in markets:
					market = appt["Lead__r"]["county__c"].title()
					sales_tmrw[market] += 1
					sales_tmrw["total"] += 1
		elif appt["Lead__r"]["county__c"]:
			if appt["Lead__r"]["county__c"].title() in markets:
				market = appt["Lead__r"]["county__c"].title()
				sales_tmrw[market] += 1
				sales_tmrw["total"] += 1

fill_set_details()
set_distribution()
sales_appts_tmrw()

date = str(now_est_aware.month) + "/" + str(now_est_aware.day)

info = {"markets": markets, "sales_today": sales_today, "g2g_today": g2g_today, "permits_today": permits_today, "sales_tw": sales_tw, "permits_tw": permits_tw, "g2g_tw": g2g_tw,
	 	"total_cads_tmrw": total_cads_tmrw, "potential_sits": potential_sits, "sits": sits, "cad_outcomes": cad_outcomes, "nmt": nmt, "cancels": cancels, "sit_rate": sit_rate,
	 	"g2g_rate": g2g_rate, "distribution": distribution, "set_details": set_details, "sales_tmrw": sales_tmrw, "sources": sources, "total_sets_today": total_sets_today,
	 	"close_rate": close_rate, "date": date, "check": now_est_aware.day}

data_file = open("/root/lboard/data.json", "w")
json.dump(info, data_file)
data_file.close()