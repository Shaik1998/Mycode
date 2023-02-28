import requests
import xmltodict
import json
import datetime
from datetime import datetime 
import logging
from dotenv import dotenv_values

config_params = dotenv_values("/root/microbot-platform/microbot/poll_trigger/trigger.env")
ticket_username = config_params['username']
ticket_password = config_params['password']
ticket_url  = config_params['url']
airwave_user = config_params['user']
airwave_pass =config_params['pass']

logging.basicConfig(filename="pollingscript_ticketcreation.log",level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')


def create_ticket(Short_description, Description):

    Service_Offering='46168a01db50e410eb43593cd396195d'
    Assignment_group='3867f5a6db0b9010d21b055cd39619e6'
    Category= "Proactive issue"
    Contact_Type= "email"
    Priority=4
    Caller="a23190a51bf46d90a64d6654b24bcbad"
    Impact=4
    Urgency=3

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"caller_id": Caller, "short_description": Short_description, "description": Description, "service_offering": Service_Offering, "assignment_group": Assignment_group, "category": Category, "contact_type": Contact_Type, "priority": Priority, "impact":Impact, "urgency":Urgency }
    try:
        response = requests.post(ticket_url, auth=(ticket_username, ticket_password), headers= headers, data= json.dumps(payload))
        data = response.json()

        if response.status_code == 201:
            print("Ticket created successfully")
            logging.info("Ticket created successfully")
        else:
            logging.error("Failed to create ticket. Response code: " + response.status_code)
            raise Exception("Failed to create ticket. Response code: " + response.status_code)
    except  Exception as e:
        logging.error(e)
        print("An error occurred while creating the ticket. Response code: " + response.status)

#Login to Airwave url
url = ""

payload='credential_0={}&credential_1={}&destination=%2Fapi'.format(airwave_pass,airwave_pass)

headers = {
  'Content-Type': 'application/x-www-form-urlencoded'
}

session=requests.Session()
response = session.post(url, headers=headers, data=payload, verify=False)
result = response.status_code

if result==200:
    cookies = session.cookies
    #trigger alert API
    url1 = "https://airwave-europe1.s2.ms.unilever.com/alerts.xml"

    headers1 = {
      'Content-Type': 'application/xml',
      'Authorization': 'Basic a290aGFyaWI6S290aDRyaWItMDAx'
    }

    response1 = session.get(url1, headers=headers1, verify=False)
    my_dict1 = xmltodict.parse(response1.text)
    json_data1 = json.dumps(my_dict1)
    data1 = json.loads(json_data1)
#    print(data1)
    Result = data1["amp:amp_alert"]["record"]
    list1 = []
    list2=[]
    for i in Result:
        down = i["type"]["@ascii_value"]
        if down == "Device Down":
            deviceType = i["summary"]["@ascii_value"]
            if ("Access Point" in deviceType):
                APName = i["triggering_agent"]["@ascii_value"]
                FirstName = APName.split('-')[0]
                timedate = i["creation_time"]["@ascii_value"]
                dict1 = {"apname" : APName, "firstname" : FirstName, "timedate" : timedate}
                list1.append(dict1)
                
            elif ("Controller" in deviceType):
                Controller = i["triggering_agent"]["@ascii_value"]
                timedate2 = i["creation_time"]["@ascii_value"]
                dict2 = {"apname" : APName, "timedate" : timedate}
                list2.append(dict2)
#ap           
    print(list1)
    current_time = datetime.now()
    print(type(current_time))
    filtered_list = []
    for record in list1:
        item_time= datetime.strptime(record['timedate'], '%m/%d/%Y %I:%M %p UTC')
        time_diff = current_time - item_time
        if time_diff.total_seconds() <= 259200:
            filtered_list.append(record)
    print(filtered_list)
    print(len(filtered_list))

    groups = []
    # Loop through the list of access points
    for i, ap in enumerate(filtered_list):
        # Extract the first name
        firstname = ap['firstname']
        # Check if this access point is in the same group as the previous one
        if i == 0 or firstname != filtered_list[i-1]['firstname']:
            # If not, create a new group with this access point
            groups.append([ap])
        else:
            # If so, add the access point to the existing group
            groups[-1].append(ap)
    print(groups)

    group_apnames = {}
    for group in groups:
        apnames=[]
        for i in group:
            apnames.append([i['apname'],i['timedate']])
        group_apnames[i['firstname']]=apnames
    print(group_apnames)
    
    note ="AP is Down - airwave-europe1.s2.ms.unilever.com - "
    desc = """ Device Down: Device Type is Access Point and Minutes Down Threshold >= 45 minutes
    Severity: Minor     
    Notes: AP is down
    
    {}
      
    """
    for i in group_apnames.keys():
        apdown_apnames= []
        ap_names_and_times = ""
        group_limit= [group_apnames[i][j:j+10] for j in range(0, len(group_apnames[i]), 10)]
        for entries in group_limit:
            for entry in entries:
                ap_names_and_times += "AP Names: {}\nTime: {}\n\n".format(entry[0], entry[1])
                apdown_apnames.append(entry[0])
            merged_text = desc.format(ap_names_and_times)
            logging.info("Creating ticket - short Description :{} - Description: {}".format(note+str(apdown_apnames),merged_text))
            create_ticket(note+str(apdown_apnames),merged_text)
#controllers       
    print(list2)
    filtered_list1 = []
    for record1 in list2:
        item_time1= datetime.strptime(record1['timedate'], '%m/%d/%Y %I:%M %p UTC')
        time_diff1 = current_time - item_time1
        if time_diff1.total_seconds() <= 259200:
            filtered_list1.append(record1)
    print(filtered_list1)
  
    for i in filtered_list1:
        note ="Controller Down - airwave-apacamet1.s2.ms.unilever.com - "
        desc = """ Device Down: Device Type is Controller and Minutes Down Threshold >= 45 minutes
        Severity: Minor   
        Time: {}
        Notes: Controller is down
        Controller Names : {}
        """.format(i['contollername'],i['timedate1'])
        short_desc="Controller Down - airwave-apacamet1.s2.ms.unilever.com -{}".format(i['contollername'])
        logging.info("Creating ticket - {} - {}".format(short_desc,desc))
        create_ticket(short_desc,desc)



