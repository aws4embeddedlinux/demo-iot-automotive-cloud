import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Handler } from './handler';
import { Provider } from './provider';
import { SignalCatalog } from './signalcatalog';

export class VehicleInterface {
  protected intf: object;

  constructor() {
    this.intf = {};
  }

  toObject(): object {
    return (this.intf);
  }
}

export interface VehicleInterfaceProps {
  readonly interfaceId: string;
  readonly name: string;
  readonly protocolName?: string;
  readonly protocolVersion?: string;
}

export class CanVehicleInterface extends VehicleInterface {
  constructor(props: VehicleInterfaceProps) {
    super();

    this.intf = {
      type: 'CAN_INTERFACE',
      interfaceId: props.interfaceId,
      canInterface: {
        name: props.name,
        protocolName: props.protocolName || 'CAN',
        protocolVersion: props.protocolVersion || '2.0b',
      },
    };
  }
}

export class MiddlewareVehicleInterface extends VehicleInterface {
  constructor(props: VehicleInterfaceProps) {
    super();

    this.intf = {
      type: 'VEHICLE_MIDDLEWARE',
      interfaceId: props.interfaceId,
      vehicleMiddleware: {
        name: props.name || 'ros2',
        protocolName: props.protocolName || 'ROS_2',
      },
    };
  }
}

export class VehicleSignal {
  protected signal: object;

  constructor() {
    this.signal = {};
  }

  toObject(): object {
    return (this.signal);
  }
}

export interface CanVehicleSignalProps {
  readonly fullyQualifiedName: string;
  readonly interfaceId: string;
  readonly messageId: number;
  readonly name?: string;
  readonly factor: number;
  readonly isBigEndian: boolean;
  readonly isSigned: boolean;
  readonly length: number;
  readonly offset: number;
  readonly startBit: number;
}

export interface MessageVehicleSignalProps {
  readonly fullyQualifiedName: string;
  readonly interfaceId: string;
  readonly messageSignal: MessageSignal;
}

export class MessageSignal extends VehicleSignal {
  constructor(props: MessageSignalProps) {
    super();

    this.signal = {
      messageSignal: {
        ...props,
      },
    };
  }

}
export class Message {
  protected m: object;

  constructor() {
    this.m = {};
  }

  toObject(): object {
    return (this.m);
  }

}

export interface MessageSignalProps {
  readonly topicName: string;
  readonly structuredMessage: StructuredMessage;
}

export class StructuredMessage extends Message {
  constructor(props: StructuredMessageProps) {
    super();

    this.m = {
      structuredMessage: {
        ...props,
      },
    };
  }
}


export interface StructuredMessageDefinitionProps {
  readonly fieldName: string;
  readonly dataType: DataType;
}

export class SignalDecoderNode {
  protected node: object;

  constructor() {
    this.node = {};
  }

  toObject(): object {
    return (this.node);
  }
}


export class StructuredMessageDefinition extends SignalDecoderNode {
  constructor(props: StructuredMessageDefinitionProps) {
    super();

    this.node = {
      structuredMessageDefinition: {
        ...props,
      },
    };
  }
}

export class PrimitiveMessageDefinition extends SignalDecoderNode {
  constructor(props: PrimitiveMessageDefinitionProps) {
    super();

    this.node = {
      ros2PrimitiveMessageDefinition: {
        ...props,
      },
    };
  }
}

export class StructuredMessageListDefinition extends SignalDecoderNode {
  constructor(props: StructuredMessageListDefinitionProps) {
    super();

    this.node = {
      structuredMessageListDefinition: {
        ...props,
      },
    };
  }
}


export class DataTypeDef {
  protected type: object;

  constructor() {
    this.type = {};
  }

  toObject(): object {
    return (this.type);
  }
}

export class DataType extends DataTypeDef {
  constructor(props: StructuredMessageProps) {
    super();

    this.type = {
      dataType: {
        ...props,
      },
    };
  }
}

export interface StructuredMessageProps {
  readonly structuredMessageDefinition?: StructuredMessageDefinition[];
  readonly primitiveMessageDefinition?: PrimitiveMessageDefinition;
  readonly structuredMessageListDefinition?: StructuredMessageListDefinition;
}

export interface PrimitiveMessageDefinitionProps {
  readonly ros2PrimitiveMessageDefinition: Ros2PrimitiveMessageDefinition;
}

export interface Ros2PrimitiveMessageDefinition {
  readonly primitiveType: string;
}

export interface StructuredMessageListDefinitionProps {
  readonly name: string;
  readonly memberType: DataType;
  readonly capacity: number;
  readonly listType: string;
}

export class CanVehicleSignal extends VehicleSignal {
  constructor(props: CanVehicleSignalProps) {
    super();

    this.signal = {
      type: 'CAN_SIGNAL',
      fullyQualifiedName: props.fullyQualifiedName,
      interfaceId: props.interfaceId,
      canSignal: {
        factor: props.factor,
        isBigEndian: props.isBigEndian,
        isSigned: props.isSigned,
        length: props.length,
        messageId: props.messageId,
        name: props.name || '',
        offset: props.offset,
        startBit: props.startBit,
      },
    };
    if (!props.name) {
      // remove description property if it is not set (FleetWise expects 1 or more characters)
      delete (this.signal as any).canSignal.name;
    }
  }
}

export class MessageVehicleSignal extends VehicleSignal {
  constructor(props: object) {
    super();
    this.signal = props;
  }
}

/**
 * Attribute Signal - needed when creating a vehicle with attributes
 */
export interface AttributeVehicleSignalProps {
  readonly fullyQualifiedName: string;
}

export class AttributeVehicleSignal extends VehicleSignal {
  constructor(props: AttributeVehicleSignalProps) {
    super();

    this.signal = {
      type: 'ATTRIBUTE_SIGNAL',
      fullyQualifiedName: props.fullyQualifiedName,
    };
  }
}

export class NetworkFileDefinition {
  protected definition: object;

  constructor() {
    this.definition = {};
  }

  toObject(): object {
    return (this.definition);
  }
}

export class CanDefinition extends NetworkFileDefinition {
  constructor(
    networkInterface: string,
    signalsMap: Record<string, string>,
    canDbcFiles: Array<string>,
  ) {
    super();


    this.definition = {
      canDbc: {
        canDbcFiles: canDbcFiles.map(file => Buffer.from(file).toString('base64')),
        networkInterface,
        signalsMap,
      },
    };
  }
}

export interface VehicleModelProps {
  readonly signalCatalog: SignalCatalog;
  readonly name: string;
  readonly description?: string;
  readonly networkInterfaces: VehicleInterface[];
  readonly signals?: VehicleSignal[];
  readonly signalsJson?: MessageVehicleSignal[];
  readonly networkFileDefinitions?: NetworkFileDefinition[];
  readonly isPreview?: boolean;
}

export class VehicleModel extends Construct {
  readonly name: string = '';
  readonly signalCatalog: SignalCatalog = ({} as SignalCatalog);
  readonly isPreview: boolean = false;

  constructor(scope: Construct, id: string, props: VehicleModelProps) {
    super(scope, id);

    (this.name as string) = props.name || '';
    (this.signalCatalog as SignalCatalog) = props.signalCatalog;

    const handler = new Handler(this, 'Handler', {
      handler: 'vehiclemodelhandler.on_event',
    });

    const isComplete = new Handler(this, 'IsCompleteHandler', {
      handler: 'vehiclemodelhandler.is_complete',
    });

    const provider = Provider.getOrCreate(
      this,
      handler,
      isComplete,
      cdk.Duration.minutes(5),
    );

    this.isPreview = props.isPreview || false;
    const REGION= this.isPreview ? 'us-west-2' : cdk.Aws.REGION;
    const resource = new cdk.CustomResource(this, 'Resource', {
      serviceToken: provider.provider.serviceToken,
      properties: {
        name: this.name,
        signal_catalog_arn: props.signalCatalog.arn,
        model_manifest_arn: `arn:aws:iotfleetwise:${REGION}:${cdk.Aws.ACCOUNT_ID}:model-manifest/${this.name}`,
        description: props.description,
        network_interfaces: JSON.stringify(props.networkInterfaces.map(i => i.toObject())),
        signals: (props.signals) ? JSON.stringify(props.signals.map(s => s.toObject())) : '{}',
        signalsJson: (props.signalsJson) ? JSON.stringify(props.signalsJson.map(s => s.toObject())) : '{}',
        network_file_definitions: (props.networkFileDefinitions) ? JSON.stringify(props.networkFileDefinitions.map(s => s.toObject())) : '{}',
      },
    });

    resource.node.addDependency(this.signalCatalog);
  }
}
