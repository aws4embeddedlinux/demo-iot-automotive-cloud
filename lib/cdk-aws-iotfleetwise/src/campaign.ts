import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Handler } from './handler';
import { Provider } from './provider';
import { Vehicle } from './vehicle';

export class CollectionScheme {
  protected scheme: object;

  constructor() {
    this.scheme = {};
  }

  toObject(): object {
    return (this.scheme);
  }
}

export class TimeBasedCollectionScheme extends CollectionScheme {
  constructor(
    period: cdk.Duration,
  ) {
    super();

    this.scheme = {
      timeBasedCollectionScheme: {
        periodMs: period.toMilliseconds(),
      },
    };
  }
}

export class ConditionBasedCollectionScheme extends CollectionScheme {
  constructor(
    conditionLanguageVersion: number,
    expression: string,
    minimumTriggerIntervalMs: number,
    triggerMode: string,
  ) {
    super();

    this.scheme = {
      conditionBasedCollectionScheme: {
        conditionLanguageVersion,
        expression,
        minimumTriggerIntervalMs,
        triggerMode,
      },
    };
  }
}

export class CampaignSignal {
  private signal: object;
  constructor(
    name: string,
    maxSampleCount?: number,
    minimumSamplingInterval?: cdk.Duration) {

    this.signal = {
      name,
      ...maxSampleCount && { maxSampleCount },
      ...minimumSamplingInterval && { minimumSamplingInterval },
    };
  }

  toObject(): object {
    return (this.signal);
  }
}

/*
export class DataDestinationConfig {

  protected destinationConfig: object;

  constructor() {
    this.destinationConfig = {};
  }

  toObject(): object {
    return (this.destinationConfig);
  }
}

export class S3ConfigProperty extends DataDestinationConfig {

  constructor(
    bucketArn: string,
    dataFormat?: string,
    prefix?: string,
    storageCompressionFormat?: string,
  ) {
    super();

    this.destinationConfig = {
      s3Config: {
        bucketArn: bucketArn,
        dataFormat: dataFormat,
        prefix: prefix,
        storageCompressionFormat: storageCompressionFormat,
      },
    };
  }
}


export class TimestreamConfigProperty extends DataDestinationConfig {

  constructor(
    executionRoleArn: string,
    timestreamTableArn: string) {
    super();
    this.destinationConfig = {
      timestreamConfig: {
        executionRoleArn: executionRoleArn,
        timestreamTableArn: timestreamTableArn,
      },
    };
  };
}


export interface CampaignProps {
  readonly name: string;
  readonly target: Vehicle;
  readonly collectionScheme: CollectionScheme;
  readonly signals: CampaignSignal[];
  readonly autoApprove?: boolean;
  readonly dataDestinationConfigs: DataDestinationConfig[];
}
*/


export interface CampaignProps {
  readonly name: string;
  readonly target: Vehicle;
  readonly collectionScheme: CollectionScheme;
  readonly signals: CampaignSignal[];
  readonly autoApprove?: boolean;
  readonly useS3?: boolean;
  readonly campaignS3arn: string;
  readonly dataFormat?: string;
  readonly storageCompressionFormat?: string;
  readonly prefix?: string;
  readonly timestreamArn: string;
  readonly fwTimestreamRole: string;
  readonly spoolingMode?: string;
  readonly postTriggerCollectionDuration?: number;
  readonly compression?: string;
  readonly endpoint?: string;
}


/**

export class Campaign extends Construct {
  readonly name: string = '';
  readonly arn: string = '';
  readonly target: Vehicle = ({} as Vehicle);

  constructor(scope: Construct, id: string, props: CampaignProps) {
    super(scope, id);

    (this.name as string) = props.name;
    this.arn = `arn:aws:iotfleetwise:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:vehicle/${props.target}`;
    (this.target as Vehicle) = props.target;

    const handler = new Handler(this, 'Handler', {
      handler: 'campaignhandler.on_event',
    });

    const resource = new cdk.CustomResource(this, 'Resource', {
      serviceToken: Provider.getOrCreate(this, handler).provider.serviceToken,
      properties: {
        name: this.name,
        signal_catalog_arn: this.target.vehicleModel.signalCatalog.arn,
        data_destination_configs: JSON.stringify(props.dataDestinationConfigs.map(s => s.toObject())),
        target_arn: this.target.arn,
        collection_scheme: JSON.stringify(props.collectionScheme.toObject()),
        signals_to_collect: JSON.stringify(props.signals.map(s => s.toObject())),
        auto_approve: props.autoApprove || false,
      },
    });
    resource.node.addDependency(this.target);
  }
}
*/


export class Campaign extends Construct {
  readonly name: string = '';
  readonly arn: string = '';
  readonly target: Vehicle = ({} as Vehicle);
  readonly endpoint?: string;

  constructor(scope: Construct, id: string, props: CampaignProps) {
    super(scope, id);

    (this.name as string) = props.name;
    this.endpoint = props.endpoint;
    this.arn = `arn:aws:iotfleetwise:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:vehicle/${props.target}`;
    (this.target as Vehicle) = props.target;

    const handler = new Handler(this, 'Handler', {
      handler: 'campaignhandler.on_event',
      endpoint: this.endpoint,
    });

    const resource = new cdk.CustomResource(this, 'Resource', {
      serviceToken: Provider.getOrCreate(this, handler).provider.serviceToken,
      properties: {
        name: this.name,
        signal_catalog_arn: this.target.vehicleModel.signalCatalog.arn,
        target_arn: this.target.arn,
        collection_scheme: JSON.stringify(props.collectionScheme.toObject()),
        signals_to_collect: JSON.stringify(props.signals.map(s => s.toObject())),
        auto_approve: props.autoApprove || false,
        post_trigger_collection_duration: props.postTriggerCollectionDuration,
        compression: props.compression || 'SNAPPY',
        useS3: props.useS3 || false,
        campaign_s3_arn: props.campaignS3arn,
        prefix: props.prefix,
        timestream_arn: props.timestreamArn,
        fw_timestream_role: props.fwTimestreamRole,
        spooling_mode: props.spoolingMode || 'OFF',
      },
    });
    resource.node.addDependency(this.target);
  }
}
