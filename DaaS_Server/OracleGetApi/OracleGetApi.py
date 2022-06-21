import requests
import os
#from os import environ
from json import loads
from math import ceil
import boto3
from  base64 import b64decode
from botocore.exceptions import ClientError
import logging
logging.getLogger().setLevel(logging.INFO)

account = os.environ['account']
region = os.environ['region']
secretname = os.environ['secretname']
url = os.environ['url']

#Function to call the Oracle URL    
def callurl(pages, lim, pgno, username, password, base_url):
    s = requests.Session()   #session initiation
    s.auth = (username, password)  # session authorization
    logging.info(f"The API url is {url}{pages}")
    #url = base_url + pages         # URL after adding the query parameters
    x = s.get(base_url + pages)                 # API call
    try:
        x_json = x.json()          # Convert response to json
    except ValueError:
        x_json = x.text     #To accomodate "Non queriable fields" error which has text output.
    if type(x_json) == dict:
        x_json.pop("links")   #pop links from json output
        x_json["status"] = "Success"
        page = int(x_json["totalResults"] / lim)   #to determin total pages
        x_json["totalPages"] = ceil(x_json["totalResults"] / lim)       
        x_json["totalItems"] = x_json["totalResults"]
        x_json.pop("totalResults")
        x_json["currentPage"] = min(pgno, x_json["totalPages"])
        x_json.pop("limit")
        x_json.pop("offset")
    return x_json  
 
# Function to load all the pages and their data to a single variable for partial match analysis.        
def loadingallpages(totalResults, Idfield, valfield, username, password, base_url ):  # defaultvalues
    i = 0
    url = {}
    lim = 500  # maximum limit of the Oracle API
    num = ceil(totalResults / lim) #total pages. (Defined twice in the same code. Can be called.)
    allpagedata = []   # variable store all the data results
    s = requests.Session()             # session initiation
    s.auth = (username, password)    # session authorization
    while i < num:  # Check for more results
        Offset = lim * i  # Offset increment 
        i = i + 1
        # Page generation with only two fields (The required partial match field and unique ID field to reduce API response time)
        pages = ('?limit=' + str(lim) + '&offset=' + str(Offset) + '&onlyData=True' + '&totalResults=True'
                 + '&fields=' + Idfield + "," + valfield) 
        Url = base_url + pages   # URL to store all the pages to be loaded 
        
        url.update({i: Url})   # Upload to a dictionary that maps urls to pages
        for x in url.values():  # loop to get all the json response data and store them in single variable
            j = s.get(x)
            allpagedata.append(j.json())
            return allpagedata       
 
# Function to generate the required string to pass as ERP API call.      
def lambda_handler(event,context):
    
    secret_name = "arn:aws:secretsmanager:"+region+":"+account+":secret:"+secretname
    region_name = region

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.
    get_secret_value_response = ""
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        l ={'DecryptionFailureException', 'InternalServiceErrorException', 'InvalidParameterException', 'InvalidRequestException', 'ResourceNotFoundException'}
        if e.response['Error']['Code'] in l:
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = b64decode(get_secret_value_response['SecretBinary'])
    
    # Get secrets and map them.
    secret = get_secret_value_response['SecretString'];
    secretstring = loads(secret)
    username = secretstring['username']
    password = secretstring['password']
    db_url = url
    
    # Take in input data and flag.
    input = event
    data = event["x_json"]
    flag = input["flag"]
    logging.info(f"The flag is {flag}")
    dataObjectID = str(data["dataObjectID"])
    dataObject = secretstring[dataObjectID]
    base_url = db_url + dataObject    
    
    offset = data["offset"] if "offset" in data else 0
    
    if 'limit' in data:
        lim = 25 if data["limit"] >25 else data["limit"]
    else: lim =10
        
    pgno = data["page"] if "page" in data else 1

    # get all query
    if flag == 0:  
        dskip = (pgno - 1) * lim if pgno>1 else offset
        pages = (f"?limit={lim}&offset={dskip}&onlyData=True&totalResults=True") 
        x_json = callurl(pages, lim, pgno, username, password, base_url)
        
    elif flag == 2:  #get all results for partial match
        IDkey = "ID" + str(data["dataObjectID"])
        Idfield = secretstring[IDkey]
            
        search_field = data["criteria"]["1"]["field"] # The field for partial match search
        pages = (f"?limit=1&onlyData=True&totalResults=True&fields={Idfield}")
        op = callurl(pages, 1, pgno, username, password, base_url )
        # x_partial variable will store the two field data for all the results within the dataObject
        x_partial = loadingallpages(op["totalItems"], Idfield, search_field,  username, password, base_url)
        search_val = data["criteria"]["1"]["value"]  # Value to be searched for partial match
        partial_matchList = []
        # Loop to perform partial match
        '''
        for i in range(len(x_partial[0]["items"])):
            if search_val in x_partial[0]["items"][i][search_field]:
                partial_matchList.append(x_partial[0]["items"][i][Idfield])   
        '''        
        partial_matchList = [x_partial[0]["items"][i[0]][Idfield] for i in enumerate(x_partial[0]["items"]) \
                            if search_val in x_partial[0]["items"][i[0]][search_field]]        
        # partial_matchList variable stores the UniqueID of all the data results that contain the partial string        
        res = []
        # Loop to fetch the data of all the rows that partially match
        print(partial_matchList)
        for x in partial_matchList:
            pages = "?q=" + Idfield + "=" + str(x) + "&onlyData=True" + "&totalResults=True"
            response = callurl(pages, lim, pgno, username, password, base_url )
            res.append(response["items"])
        x_json = {}
        x_json["status"] = "Success"
        x_json["totalResults"] = len(partial_matchList)
        x_json["totalPages"] = ceil(x_json["totalResults"] / lim)
        x_json["currentPage"] = pgno
        for i in range(len(res)):
            res[i] = res[i][0]
        if pgno == 1:
            if lim <= x_json["totalResults"]:
                x_json["items"] = res[0:lim]
                x_json["count"] = lim
            else:
                x_json["items"] = res
                x_json["count"] = len(partial_matchList)
        elif pgno > 1:
            skip = lim * (pgno - 1)
            if lim <= x_json["totalResults"]:
                x_json["items"] = res[skip:skip + (lim - 1)]
                x_json["count"] = x_json["totalResults"] - lim * (pgno - 1)
            else:
                x_json["items"] = res[skip:-1]
                x_json["count"] = x_json["totalResults"]

    elif flag==1:
        qfl = []
        for i in enumerate(data["criteria"]):      #in between type operator processing
            if type(data["criteria"][i[1]]["value"]) == dict:
                qf = data["criteria"][i[1]]['field'] + '>=' + str(
                    min(data["criteria"][i[1]]["value"]["value1"],
                        data["criteria"][i[1]]["value"]["value2"])) + " and " + "<=" + str(
                    max(data["criteria"][i[1]]["value"]["value1"],
                        data["criteria"][i[1]]["value"]["value2"]))
                qfl.append(qf)
            else:
                qf = data["criteria"][i[1]]['field'] + data["criteria"][i[1]]['operator'] + \
                     data["criteria"][i[1]]['value']
                qfl.append(qf)
        queryfilter = ";".join(qfl)
        dskip = (pgno - 1) * lim if pgno>1 else offset
        pages = (f"?limit={lim}&offset={dskip}&q={queryfilter}&onlyData=True&totalResults=True")
        x_json = callurl(pages, lim, pgno, username, password, base_url)  
        
    elif flag==3:
        qfl = []
        for i in enumerate(data["criteria"]):      #in between type operator processing
            if type(data["criteria"][i[1]]["value"]) == dict:
                qf = data["criteria"][i[1]]['field'] + '>=' + str(
                    min(data["criteria"][i[1]]["value"]["value1"],
                        data["criteria"][i[1]]["value"]["value2"])) + " and " + "<=" + str(
                    max(data["criteria"][i[1]]["value"]["value1"],
                        data["criteria"][i[1]]["value"]["value2"]))
                qfl.append(qf)
            else:
                qf = data["criteria"][i[1]]['field'] + data["criteria"][i[1]]['operator'] + \
                     data["criteria"][i[1]]['value']
                qfl.append(qf)
        queryfilter = ";".join(qfl)
        
        #temp
        xxx = ['CountryLookup',
 'FiscalYearEndMonthLookup',
 'ParentSupplierLookup',
 'CurrencyLookup',
 'BusinessRelationshipLookup',
 'TaxOrganizationTypeLookup',
 'SupplierTypeLookup',
 'FederalIncomeTaxTypeLookup',
 'WithholdingTaxGroupLookup',
 'DFF',
 'addresses',
 'attachments',
 'businessClassifications',
 'contacts',
 'globalDFF',
 'productsAndServices',
 'sites']
        exp = ','.join(xxx)
        pages = (f"?q={queryfilter}&expand={exp}&onlyData=True&totalResults=True")
        x_json = callurl(pages, lim, pgno, username, password, base_url)    
        print(x_json) 
        a = {j:x_json['items'][0].pop(j) for j in xxx if x_json['items'][0][j]} 
        logging.info(f"This is the sublinkdata {a}")
        
    if flag < 0:
        x_json ={}
    
    try:
        sublink = a
    except Exception:
        sublink = None
    
    #return x_json    
    output = {
        'x_json' : x_json,
        'sublinkData': sublink,
        'data' : event
    }
    return output    

