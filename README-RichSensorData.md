## Deploying Biga with the Rich Sensor Data Preview Feature

Notes: 
- This feature is only available in Gamma, in us-west-2. 
- Your AWS Accounts need to be fully allow-listed in order to deploy and test this feature.
- Deployments of all the Biga stacks for this feature are restricted to us-west-2.

## Commands

`npm install -g aws-cdk`

Ensure correct account, region and exported keys.

`cdk bootstrap`

`cd demo-auto-aws-iotfleetwise`

`python3 -m venv .venv`

`source .venv/bin/activate`

`pip install -r requirements.txt`

In the lib folder, go to the package.json lib file and run the `build`, and `package:python` scripts. 

`
pip install lib/cdk-aws-iotfleetwise/dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz

`cdk deploy --all --require-approval never`

## Known issues
- The update operation is not implemented for all Custom Resources. So you can still experience failed updates, failed delete etc. 
- This integration is still under heavy development. We will continue doing bug fixes and improvements. 