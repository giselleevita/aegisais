/* eslint-disable */

// Auto-generated from JSON Schema. Do not edit manually.

import type { FromSchema } from "json-schema-to-ts";

export const AlertSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Alert.schema.json",
  "title": "Alert",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "alertType",
    "status",
    "createdAt",
    "priority",
    "message",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "alertType": {
      "type": "string"
    },
    "eventId": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "enum": [
        "new",
        "triaged",
        "acknowledged",
        "resolved",
        "closed"
      ]
    },
    "priority": {
      "type": "string",
      "enum": [
        "p4",
        "p3",
        "p2",
        "p1"
      ]
    },
    "message": {
      "type": "string"
    },
    "assignee": {
      "type": "string"
    },
    "createdAt": {
      "type": "string",
      "format": "date-time"
    },
    "acknowledgedAt": {
      "type": "string",
      "format": "date-time"
    },
    "resolvedAt": {
      "type": "string",
      "format": "date-time"
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const AssetSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Asset.schema.json",
  "title": "Asset",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "organisationId",
    "assetType",
    "name",
    "status",
    "criticality",
    "geometry",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "organisationId": {
      "type": "string"
    },
    "assetType": {
      "type": "string",
      "enum": [
        "cable_segment",
        "landing_station",
        "patrol_zone",
        "sensor_node"
      ]
    },
    "name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "criticality": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high",
        "critical"
      ]
    },
    "geometry": {
      "type": "object",
      "additionalProperties": true
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const ConfidenceSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Confidence.schema.json",
  "title": "Confidence",
  "$ref": "_common.json#/$defs/Confidence"
} as const;

export const DeviceSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Device.schema.json",
  "title": "Device",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "organisationId",
    "deviceType",
    "name",
    "status",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "organisationId": {
      "type": "string"
    },
    "assetId": {
      "type": "string"
    },
    "deviceType": {
      "type": "string",
      "enum": [
        "gateway",
        "sensor",
        "collector"
      ]
    },
    "name": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "firmwareVersion": {
      "type": "string"
    },
    "certificateRef": {
      "type": "string"
    },
    "connectivityProfile": {
      "type": "object",
      "additionalProperties": true
    },
    "location": {
      "$ref": "_common.json#/$defs/GeoPoint"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const DeviceHeartbeatSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/DeviceHeartbeat.schema.json",
  "title": "DeviceHeartbeat",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "deviceId",
    "recordedAt",
    "status"
  ],
  "properties": {
    "deviceId": {
      "type": "string"
    },
    "recordedAt": {
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "type": "string"
    },
    "batteryLevel": {
      "type": "number"
    },
    "queueDepth": {
      "type": "integer"
    },
    "signalStrength": {
      "type": "number"
    },
    "details": {
      "type": "object",
      "additionalProperties": true
    }
  }
} as const;

export const EntitySchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Entity.schema.json",
  "title": "Entity",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "entityType",
    "observedAt",
    "updatedAt",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "entityType": {
      "type": "string"
    },
    "aliases": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "position": {
      "$ref": "_common.json#/$defs/GeoPoint"
    },
    "heading": {
      "type": "number"
    },
    "speed": {
      "type": "number"
    },
    "status": {
      "type": "string"
    },
    "observedAt": {
      "type": "string",
      "format": "date-time"
    },
    "updatedAt": {
      "type": "string",
      "format": "date-time"
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const EventSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Event.schema.json",
  "title": "Event",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "eventType",
    "entityIds",
    "occurredAt",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "eventType": {
      "type": "string"
    },
    "incidentId": {
      "type": "string"
    },
    "entityIds": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "geometry": {
      "$ref": "_common.json#/$defs/GeoPoint"
    },
    "occurredAt": {
      "type": "string",
      "format": "date-time"
    },
    "endedAt": {
      "type": "string",
      "format": "date-time"
    },
    "severity": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high",
        "critical"
      ]
    },
    "attributes": {
      "type": "object",
      "additionalProperties": true
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const ImportBundleSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/ImportBundle.schema.json",
  "title": "ImportBundle",
  "description": "Batch import payload for historical AIS track data (BL-011 competitor migration, BL-015 interoperability profile)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "bundleId",
    "sourceFormat",
    "organisationId",
    "createdAt",
    "tracks"
  ],
  "properties": {
    "bundleId": {
      "type": "string",
      "format": "uuid"
    },
    "sourceFormat": {
      "type": "string",
      "enum": [
        "marine_traffic",
        "vessel_finder",
        "fleet_mon",
        "generic_nmea",
        "aegisais_native"
      ]
    },
    "organisationId": {
      "type": "string"
    },
    "createdAt": {
      "type": "string",
      "format": "date-time"
    },
    "schemaVersion": {
      "type": "string",
      "const": "1.0.0"
    },
    "tracks": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "./Track.schema.json"
      }
    },
    "validationReport": {
      "$ref": "#/$defs/ValidationReport"
    }
  },
  "$defs": {
    "ValidationReport": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "totalRows",
        "importedRows",
        "failedRows",
        "confidenceScore"
      ],
      "properties": {
        "totalRows": {
          "type": "integer",
          "minimum": 0
        },
        "importedRows": {
          "type": "integer",
          "minimum": 0
        },
        "failedRows": {
          "type": "integer",
          "minimum": 0
        },
        "confidenceScore": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "missingPosition": {
          "type": "integer",
          "minimum": 0
        },
        "missingTimestamp": {
          "type": "integer",
          "minimum": 0
        },
        "duplicateTrackKeys": {
          "type": "integer",
          "minimum": 0
        },
        "invalidMmsi": {
          "type": "integer",
          "minimum": 0
        },
        "driftSummary": {
          "type": "string"
        }
      }
    }
  }
} as const;

export const IncidentSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Incident.schema.json",
  "title": "Incident",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "title",
    "status",
    "entityIds",
    "eventIds",
    "alertIds",
    "createdAt",
    "updatedAt",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "title": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "enum": [
        "open",
        "monitoring",
        "contained",
        "closed"
      ]
    },
    "entityIds": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "eventIds": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "alertIds": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "summary": {
      "type": "string"
    },
    "createdAt": {
      "type": "string",
      "format": "date-time"
    },
    "updatedAt": {
      "type": "string",
      "format": "date-time"
    },
    "closedAt": {
      "type": "string",
      "format": "date-time"
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const LayerDefinitionSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/LayerDefinition.schema.json",
  "title": "LayerDefinition",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "name",
    "geometryType",
    "queryable",
    "streamable",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "geometryType": {
      "type": "string"
    },
    "entityType": {
      "type": "string"
    },
    "queryable": {
      "type": "boolean"
    },
    "streamable": {
      "type": "boolean"
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const ObservationSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Observation.schema.json",
  "title": "Observation",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "entityId",
    "layerId",
    "geometry",
    "observedAt",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "entityId": {
      "type": "string"
    },
    "layerId": {
      "type": "string"
    },
    "geometry": {
      "$ref": "_common.json#/$defs/GeoPoint"
    },
    "properties": {
      "type": "object",
      "additionalProperties": true
    },
    "observedAt": {
      "type": "string",
      "format": "date-time"
    },
    "ingestedAt": {
      "type": "string",
      "format": "date-time"
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const ProvenanceSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Provenance.schema.json",
  "title": "Provenance",
  "$ref": "_common.json#/$defs/Provenance"
} as const;

export const SensorNodeSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/SensorNode.schema.json",
  "title": "SensorNode",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "assetId",
    "deviceId",
    "sensorType",
    "location",
    "status"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "assetId": {
      "type": "string"
    },
    "deviceId": {
      "type": "string"
    },
    "sensorType": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "location": {
      "$ref": "_common.json#/$defs/GeoPoint"
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "calibration": {
      "type": "object",
      "additionalProperties": true
    }
  }
} as const;

export const SensorReadingSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/SensorReading.schema.json",
  "title": "SensorReading",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "sensorNodeId",
    "recordedAt",
    "readingType",
    "value",
    "unit"
  ],
  "properties": {
    "sensorNodeId": {
      "type": "string"
    },
    "recordedAt": {
      "type": "string",
      "format": "date-time"
    },
    "readingType": {
      "type": "string"
    },
    "value": {
      "type": "number"
    },
    "unit": {
      "type": "string"
    },
    "quality": {
      "$ref": "./Confidence.schema.json"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
} as const;

export const TelemetryEnvelopeSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/TelemetryEnvelope.schema.json",
  "title": "TelemetryEnvelope",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "eventId",
    "sourceType",
    "sourceId",
    "recordedAt",
    "payload",
    "provenance"
  ],
  "properties": {
    "eventId": {
      "type": "string"
    },
    "sourceType": {
      "type": "string",
      "enum": [
        "mqtt",
        "nmea",
        "edge_batch",
        "api"
      ]
    },
    "sourceId": {
      "type": "string"
    },
    "recordedAt": {
      "type": "string",
      "format": "date-time"
    },
    "dedupeKey": {
      "type": "string"
    },
    "payload": {
      "type": "object",
      "additionalProperties": true
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    }
  }
} as const;

export const TrackSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/Track.schema.json",
  "title": "Track",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "entityId",
    "layerId",
    "startTime",
    "endTime",
    "points",
    "confidence",
    "provenance",
    "access"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "entityId": {
      "type": "string"
    },
    "layerId": {
      "type": "string"
    },
    "startTime": {
      "type": "string",
      "format": "date-time"
    },
    "endTime": {
      "type": "string",
      "format": "date-time"
    },
    "points": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "_common.json#/$defs/GeoPoint"
      }
    },
    "confidence": {
      "$ref": "./Confidence.schema.json"
    },
    "provenance": {
      "$ref": "./Provenance.schema.json"
    },
    "access": {
      "$ref": "_common.json#/$defs/AccessMetadata"
    }
  }
} as const;

export const CommonSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aegisais.dev/contracts/common.schema.json",
  "title": "Common Contract Types",
  "$defs": {
    "AccessMetadata": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "classification",
        "allowedRoles"
      ],
      "properties": {
        "classification": {
          "type": "string",
          "enum": [
            "public",
            "internal",
            "restricted",
            "secret"
          ]
        },
        "allowedRoles": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "compartments": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "ownerOrgId": {
          "type": "string"
        }
      }
    },
    "Confidence": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "score",
        "method"
      ],
      "properties": {
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "method": {
          "type": "string"
        },
        "lowerBound": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "upperBound": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "notes": {
          "type": "string"
        }
      }
    },
    "Provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "source",
        "processor",
        "ingestedAt"
      ],
      "properties": {
        "source": {
          "type": "string"
        },
        "sourceRecordId": {
          "type": "string"
        },
        "processor": {
          "type": "string"
        },
        "ingestedAt": {
          "type": "string",
          "format": "date-time"
        },
        "lineage": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "GeoPoint": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "coordinates"
      ],
      "properties": {
        "type": {
          "type": "string",
          "const": "Point"
        },
        "coordinates": {
          "type": "array",
          "minItems": 2,
          "maxItems": 3,
          "items": {
            "type": "number"
          }
        }
      }
    }
  }
} as const;

type SchemaReferences = [typeof AlertSchema, typeof AssetSchema, typeof ConfidenceSchema, typeof DeviceSchema, typeof DeviceHeartbeatSchema, typeof EntitySchema, typeof EventSchema, typeof ImportBundleSchema, typeof IncidentSchema, typeof LayerDefinitionSchema, typeof ObservationSchema, typeof ProvenanceSchema, typeof SensorNodeSchema, typeof SensorReadingSchema, typeof TelemetryEnvelopeSchema, typeof TrackSchema, typeof CommonSchema];

export type Alert = FromSchema<typeof AlertSchema, { references: SchemaReferences }>;

export type Asset = FromSchema<typeof AssetSchema, { references: SchemaReferences }>;

export type Confidence = FromSchema<typeof ConfidenceSchema, { references: SchemaReferences }>;

export type Device = FromSchema<typeof DeviceSchema, { references: SchemaReferences }>;

export type DeviceHeartbeat = FromSchema<typeof DeviceHeartbeatSchema, { references: SchemaReferences }>;

export type Entity = FromSchema<typeof EntitySchema, { references: SchemaReferences }>;

export type Event = FromSchema<typeof EventSchema, { references: SchemaReferences }>;

export type ImportBundle = FromSchema<typeof ImportBundleSchema, { references: SchemaReferences }>;

export type Incident = FromSchema<typeof IncidentSchema, { references: SchemaReferences }>;

export type LayerDefinition = FromSchema<typeof LayerDefinitionSchema, { references: SchemaReferences }>;

export type Observation = FromSchema<typeof ObservationSchema, { references: SchemaReferences }>;

export type Provenance = FromSchema<typeof ProvenanceSchema, { references: SchemaReferences }>;

export type SensorNode = FromSchema<typeof SensorNodeSchema, { references: SchemaReferences }>;

export type SensorReading = FromSchema<typeof SensorReadingSchema, { references: SchemaReferences }>;

export type TelemetryEnvelope = FromSchema<typeof TelemetryEnvelopeSchema, { references: SchemaReferences }>;

export type Track = FromSchema<typeof TrackSchema, { references: SchemaReferences }>;
