const { IAMClient, CreateRoleCommand, AttachRolePolicyCommand, GetRoleCommand } = require('@aws-sdk/client-iam');

const iam = new IAMClient({ region: 'us-east-1' });

const trustPolicy = {
  Version: '2012-10-17',
  Statement: [
    {
      Effect: 'Allow',
      Principal: {
        Service: 'lambda.amazonaws.com'
      },
      Action: 'sts:AssumeRole'
    }
  ]
};

async function createLambdaRole() {
  const roleName = 'remotion-lambda-role';
  
  try {
    console.log('🚀 Creating IAM role for Lambda...');
    
    // Create role
    await iam.send(new CreateRoleCommand({
      RoleName: roleName,
      AssumeRolePolicyDocument: JSON.stringify(trustPolicy),
      Description: 'Role for Remotion Lambda function'
    }));
    
    console.log('✅ Role created:', roleName);
    
    // Wait a bit for role to propagate
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Attach policies
    const policies = [
      'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
      'arn:aws:iam::aws:policy/AmazonS3FullAccess'
    ];
    
    for (const policy of policies) {
      await iam.send(new AttachRolePolicyCommand({
        RoleName: roleName,
        PolicyArn: policy
      }));
      console.log('✅ Attached policy:', policy);
    }
    
    console.log('🎯 Role ARN: arn:aws:iam::472015766211:role/' + roleName);
    return roleName;
    
  } catch (error) {
    if (error.name === 'EntityAlreadyExists') {
      console.log('✅ Role already exists:', roleName);
      return roleName;
    }
    console.error('❌ Failed to create role:', error);
    throw error;
  }
}

createLambdaRole()
  .then(roleName => {
    console.log('\n🎉 Lambda role ready:', roleName);
    process.exit(0);
  })
  .catch(error => {
    console.error('Role creation failed:', error.message);
    process.exit(1);
  });
