import boto3
import json

class FWLiveParams:
    dealfinder_mode_networkx = 1
    dealfinder_mode_neo4j = 2
    
    neo4j_mode_disabled = 1
    neo4j_mode_localhost = 2
    neo4j_mode_aws_cloud = 3

    neo4j_mode_localhost_details = {
        'uri' : 'bolt://localhost:7687',
        'user' : 'neo4j',
        'password' : 'neo' 
        }

    def __init__(self,
                 enable_plotting=False,
                 remoteDebuggingEnabled=False,
                 is_sandbox_mode=True,
                 is_forex_enabled=True,
                 results_dir='./',
                 neo4j_mode=neo4j_mode_disabled,
                 dealfinder_mode=dealfinder_mode_networkx):
        self.enable_plotting = enable_plotting
        self.is_sandbox_mode = is_sandbox_mode
        self.is_forex_enabled = is_forex_enabled
        self.results_dir = results_dir
        self.neo4j_mode = neo4j_mode
        self.remoteDebuggingEnabled=remoteDebuggingEnabled
        self.dealfinder_mode = dealfinder_mode

    @staticmethod
    def getNeo4jCredentials():
        # Read parameters from AWS SSM         
        with open('./cred/aws-keys.json') as file:
            cred = json.load(file)
            ssm = boto3.client('ssm',
                aws_access_key_id=cred['aws_access_key_id'],
                aws_secret_access_key=cred['aws_secret_access_key'],
                region_name=cred['region_name'])
            def getSSMParam(paramName):
              return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']  

        return {
                'uri' : getSSMParam('/Prod/neo4j/uri'),
                'user' : getSSMParam('/Prod/neo4j/user'),
                'password' : getSSMParam('/Prod/neo4j/password')
                }

        