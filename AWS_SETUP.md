# AWS Lambda Rights Setup

## Problem
The Remotion Lambda role `remotion-lambda-role` was missing permissions to invoke other Lambda functions, causing the error:
```
User is not authorized to perform: lambda:InvokeFunction on resource: arn:aws:lambda:us-east-1:472015766211:function:remotion-render-*
```

## Solution
Created and attached a new policy `RemotionLambdaInvokePolicy` to the role.

### Policy Content (lambda-invoke-policy.json)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:us-east-1:472015766211:function:remotion-render-*"
            ]
        }
    ]
}
```

### AWS CLI Commands Used
```bash
# Create the policy
aws iam create-policy \
  --policy-name RemotionLambdaInvokePolicy \
  --policy-document file://lambda-invoke-policy.json \
  --description "Policy to allow Remotion Lambda role to invoke other Lambda functions"

# Attach policy to role
aws iam attach-role-policy \
  --role-name remotion-lambda-role \
  --policy-arn arn:aws:iam::472015766211:policy/RemotionLambdaInvokePolicy
```

### Final Role Policies
After the fix, the `remotion-lambda-role` has these policies attached:
1. `RemotionLambdaInvokePolicy` - Custom policy for Lambda invocation
2. `AWSLambdaBasicExecutionRole` - Basic Lambda execution rights
3. `AmazonS3FullAccess` - Full S3 access

## Result
✅ Video rendering now works without authorization errors
✅ Render requests successfully start with renderId
✅ Progress polling works correctly

