import boto3
import json
import logging
import MySQLdb
import os

logger = logging.getLogger('Db')


class Database:

    @staticmethod
    def initDBFromAWSParameterStore() -> MySQLdb.Connection:
        SSM_DB_PREFIX = '/prod/db/arbitragedb'
        logger.info(f'__initDBFromAWSParameterStore')
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../cred/aws-keys.json') as file:
            cred = json.load(file)
            ssm = boto3.client('ssm',
                               aws_access_key_id=cred['aws_access_key_id'],
                               aws_secret_access_key=cred['aws_secret_access_key'],
                               region_name=cred['region_name'])

            def getSSMParam(paramName):
                return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']

            return MySQLdb.connect(host=getSSMParam(SSM_DB_PREFIX + '/host'),
                                   user=getSSMParam(SSM_DB_PREFIX + '/user'),
                                   passwd=getSSMParam(SSM_DB_PREFIX + '/password'),
                                   db=getSSMParam(SSM_DB_PREFIX + '/database'),
                                   port=int(getSSMParam(SSM_DB_PREFIX + '/port')))
