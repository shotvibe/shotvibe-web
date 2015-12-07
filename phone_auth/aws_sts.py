from django.conf import settings

import boto.sts
import json

# See:
#   https://www.whitneyindustries.com/aws/2014/11/16/boto-plus-s3-plus-sts-tokens.html
def get_s3_upload_token(user, duration=900):
    policy_to_grant = {'Statement': [{'Action': ['s3:PutObject'],
                                      'Effect': 'Allow',
                                      # TODO For security, limit permissions to
                                      # upload only to user subdirectory:
                                      'Resource': ['arn:aws:s3:::glance-uploads/*']}]}
    stsconn = boto.sts.connect_to_region('us-east-1',
                                    aws_access_key_id=settings.AWS_ACCESS_KEY,
                                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    token = stsconn.get_federation_token(name='user-' + str(user.id),
                                         duration=duration,
                                         policy=json.dumps(policy_to_grant))

    return token
