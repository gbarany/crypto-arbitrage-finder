"""
# AWS Simple Notification Service
# Crude two lines to send text/email messages to subscribers:

from Notifications import sendNotification
sendNotification("your message")

"""

import boto3
import json

snsClient = boto3.client('sns')
topicARN = "arn:aws:sns:eu-west-1:605012833506:analyser-notifications"

def sendNotification(message):
     
    with open('./cred/aws-keys.json') as file:
        cred = json.load(file)
        sns = boto3.client('sns',
            aws_access_key_id=cred['aws_access_key_id'],
            aws_secret_access_key=cred['aws_secret_access_key'],
            region_name=cred['region_name'])

    # For local testing with profile
    # session = boto3.Session(profile_name='crypto')
    # sns = session.client('sns', region_name='eu-west-1')

    response = sns.publish(TopicArn=topicARN, Message=message)
    return response