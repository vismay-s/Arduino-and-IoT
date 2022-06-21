import json
import boto3
import logging
import re
logging.getLogger().setLevel(logging.INFO)

rdsData = boto3.client('rds-data')
cluster_arn = 'arn:aws:rds:us-east-2:315952988300:cluster:aiopsd-dev'
secret_arn = 'arn:aws:secretsmanager:us-east-2:315952988300:secret:rds-db-credentials/cluster-SZJFRPBR62KMYC3JKNKOF3UGSY/daas_user-xklZ3w'

def processCheck(data):
     return -5 if not "erpid" in data or not "dataObjectID" in data or not "criteria" in data else 1


def urlSelector(data):
    if data["erpid"] == 1:
        ERP = "SAP"
    if data["erpid"] == 2:
        ERP = "Oracle"
    return ERP


def CIM(data, flag, rdsData, cluster_arn, secret_arn ):

    if flag==1:   # filter condition for correct flagging. (-3 case can be ignored for AI ML model)
        query_erp = data["erpid"]  # assigning ERP ID to variable for query string building
        x=[]
        for i in enumerate(data["criteria"]):  # Loop for CIM mapping of each indiviudal criteria within input json
            query_param = data["criteria"][i[1]]["field"]  # The query parameter which needs to be mapped
            
            query = (f"select * from cdm.cim_mapping where field_mapping_type_id = {query_erp} and \
                        common_name ='{query_param}';")  
            logging.info(query)
            # Execution statement
            response = rdsData.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database='dev',
                sql=query)
            
            x.append(response['records'])
            
            # if loop for checking successful query execution
            if response['records']:
                data["criteria"][i[1]]["field"] = response['records'][0][3]['stringValue'] # mapped field reassignment
                if response['records'][0][7]['longValue']==1:     # child table verification
                    data["criteria"][i[1]]["childTable"] = response['records'][0][8]['stringValue']  # child table reassignment
                else:
                    data["criteria"][i[1]]["childTable"] = None   # null value for parent class field
            else:                # unsuccesful or empty query response
                flag = -2        # flag for incorrect generic name from frontend
                break
    logging.info(f"The response is {x}")           
    return data, flag


def lambda_handler(event, context):
    # print(event)
    inputdata = event["data"]
    # data, flag = CM(inputdata)  # step to execute when CIM data is ready
    flag = processCheck(inputdata)  # testing method to assign flag statically.
    if flag != -5:
        data, flag = CIM(inputdata, flag, rdsData, cluster_arn, secret_arn)
        ERP = urlSelector(inputdata)
        if ERP == "SAP":
            x_json = inputdata  # Functionto call SAP: getSAP(inputdata, flag)
        if ERP == "Oracle":
            x_json = inputdata  # Function to call Oracle: getOracle(inputdata, flag)

        output = {
            'x_json': x_json,
            'ERP': ERP,
            'flag': flag
        }
    else:
        output = {"status": "Failure",
                  "message": "Mandatory Fields missing",
                  'ERP': 'None'
                  }
    logging.info(output)  
    return output
