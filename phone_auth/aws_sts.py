from django.conf import settings

import boto.sts
import json

def get_s3_upload_token(user, duration=900):
    policy_to_grant = {'Statement': [{'Action': ['s3:PutObject'],
                                      'Effect': 'Allow',
                                      'Resource': ['arn:aws:s3:::glance-uploads/*']}]}
    stsconn = boto.sts.connect_to_region('us-east-1',
                                    aws_access_key_id=settings.AWS_ACCESS_KEY,
                                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    token = stsconn.get_federation_token(name='user-' + str(user.id),
                                         duration=duration,
                                         policy=json.dumps(policy_to_grant))

    return token
