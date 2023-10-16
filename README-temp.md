`npm install -g aws-cdk`

Ensure correct account, region and exported keys.

`cdk bootstrap`

`cd demo-auto-aws-iotfleetwise`

`python3 -m venv .venv`

`source .venv/bin/activate`

`pip install -r requirements.txt`

``
pip install lib/cdk-aws-iotfleetwise/dist/python/cdk-aws-iotfleetwise-0.0.0.tar.gz
pip uninstall cdk-aws-iotfleetwise-0.0.0.tar.gz

`cdk deploy --all --require-approval never`