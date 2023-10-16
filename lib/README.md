## Why

We have copied locally(in this lib folder) the CDK FleetWise library published here: https://pypi.org/project/cdk-aws-iotfleetwise/ into the lib foldwer temporarily.
This was done in order to modify the library: import the new FleetWise API model (under testing) for Rich Sensor Data and implement the new API calls.

This work is temporary until Rich Sensor Data is released. 

## How to publish the new library? 

- call build of lib (you can do this by running the build script defined in package.json )
- call package of python version (also can be done from package json)
- pip install lib/cdk-aws-iotfleetwise/dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz
