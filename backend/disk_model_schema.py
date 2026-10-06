"""Fixed Disk Model export contract and dependency-free subset validator.

SCHEMA is mirrored to docs/disk-model-v1.schema.json; tests forbid drift. This
validator implements only the keywords used by this fixed schema. It does not
fetch remote schemas, accept user-provided schemas or claim general JSON Schema
support. Semantic references are checked in disk_model.validate_inventory.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime

SCHEMA = json.loads(r'''
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Disk Model v1 read-only observation export",
  "description": "Local observations, hypotheses and informational alternatives. Never filesystem mutation authority.",
  "type": "object",
  "properties": {
    "schema_version": {
      "const": "disk-model/v1"
    },
    "read_only": {
      "const": true
    },
    "synthetic": {
      "type": "boolean"
    },
    "scan": {
      "$ref": "#/$defs/scan"
    },
    "entries": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/entry"
      },
      "maxItems": 100000
    },
    "changes": {
      "$ref": "#/$defs/changes"
    },
    "aggregates": {
      "$ref": "#/$defs/aggregates"
    },
    "directories": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/directory"
      },
      "maxItems": 100000
    },
    "evidence": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/evidence"
      },
      "maxItems": 400000
    },
    "relationships": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/relationship"
      },
      "maxItems": 2000
    },
    "findings": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/finding"
      },
      "maxItems": 400
    },
    "plan_alternatives": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/plan"
      },
      "maxItems": 400
    },
    "analysis_coverage": {
      "type": "object",
      "properties": {
        "findings_omitted": {
          "type": "integer",
          "minimum": 0
        },
        "relationships_omitted": {
          "type": "integer",
          "minimum": 0
        },
        "max_findings": {
          "const": 400
        },
        "max_relationships": {
          "const": 2000
        },
        "semantic_content_analysis": {
          "const": false
        }
      },
      "required": [
        "findings_omitted",
        "relationships_omitted",
        "max_findings",
        "max_relationships",
        "semantic_content_analysis"
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "schema_version",
    "read_only",
    "scan",
    "entries",
    "changes",
    "aggregates",
    "directories",
    "evidence",
    "relationships",
    "findings",
    "plan_alternatives",
    "analysis_coverage"
  ],
  "additionalProperties": false,
  "$defs": {
    "fingerprint": {
      "anyOf": [
        {
          "type": "null"
        },
        {
          "type": "object",
          "properties": {
            "device": {
              "type": "integer",
              "minimum": 0
            },
            "inode": {
              "type": "integer",
              "minimum": 0
            },
            "size": {
              "type": "integer",
              "minimum": 0
            },
            "mtime_ns": {
              "type": "integer"
            },
            "ctime_ns": {
              "type": "integer"
            },
            "mode": {
              "type": "integer",
              "minimum": 0
            },
            "link_count": {
              "type": "integer",
              "minimum": 0
            }
          },
          "required": [
            "device",
            "inode",
            "size",
            "mtime_ns",
            "ctime_ns",
            "mode",
            "link_count"
          ],
          "additionalProperties": false
        }
      ]
    },
    "entry": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "root_id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "relative_path": {
          "type": "string",
          "minLength": 1,
          "maxLength": 65536,
          "pattern": "^(?:\\.|(?!\\.{1,2}(?:/|$))[^/\\u0000]+(?:/(?!\\.{1,2}(?:/|$))[^/\\u0000]+)*)$"
        },
        "parent_id": {
          "type": [
            "string",
            "null"
          ]
        },
        "kind": {
          "enum": [
            "file",
            "directory",
            "symlink",
            "special",
            "unknown"
          ]
        },
        "status": {
          "enum": [
            "observed",
            "stale",
            "disappeared",
            "unreadable",
            "unsupported",
            "excluded"
          ]
        },
        "logical_bytes": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "allocated_bytes": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "allocation_source": {
          "enum": [
            "stat_blocks_512",
            "unknown"
          ]
        },
        "object_id": {
          "type": [
            "string",
            "null"
          ]
        },
        "link_count": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "mtime_ns": {
          "type": [
            "integer",
            "null"
          ]
        },
        "ctime_ns": {
          "type": [
            "integer",
            "null"
          ]
        },
        "fingerprint": {
          "$ref": "#/$defs/fingerprint"
        },
        "hash": {
          "type": "object",
          "properties": {
            "status": {
              "enum": [
                "disabled",
                "verified",
                "stale",
                "unreadable",
                "skipped",
                "interrupted",
                "file_byte_limit",
                "hash_budget_limit",
                "placeholder_not_read"
              ]
            },
            "algorithm": {
              "enum": [
                null,
                "sha256"
              ]
            },
            "value": {
              "type": [
                "string",
                "null"
              ]
            }
          },
          "required": [
            "status",
            "algorithm",
            "value"
          ],
          "additionalProperties": false,
          "allOf": [
            {
              "if": {
                "properties": {
                  "status": {
                    "const": "verified"
                  }
                }
              },
              "then": {
                "properties": {
                  "algorithm": {
                    "const": "sha256"
                  },
                  "value": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$"
                  }
                }
              },
              "else": {
                "properties": {
                  "value": {
                    "type": "null"
                  }
                }
              }
            }
          ]
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "id",
        "root_id",
        "relative_path",
        "parent_id",
        "kind",
        "status",
        "logical_bytes",
        "allocated_bytes",
        "allocation_source",
        "object_id",
        "link_count",
        "mtime_ns",
        "ctime_ns",
        "fingerprint",
        "hash",
        "uncertainties"
      ],
      "additionalProperties": false
    },
    "limits": {
      "type": "object",
      "properties": {
        "max_entries": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100000
        },
        "max_directory_entries": {
          "type": "integer",
          "minimum": 1,
          "maximum": 20000
        },
        "max_depth": {
          "type": "integer",
          "minimum": 1,
          "maximum": 64
        },
        "max_seconds": {
          "type": "number",
          "exclusiveMinimum": 0,
          "maximum": 3600
        },
        "hash_files": {
          "type": "boolean"
        },
        "max_hash_file_bytes": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1073741824
        },
        "max_hash_total_bytes": {
          "type": "integer",
          "minimum": 1,
          "maximum": 4294967296
        },
        "max_hash_files": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000
        },
        "exclude_names": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "pattern": "^(?!\\.{1,2}$)[^/\\\\\\u0000]+$"
          },
          "maxItems": 100
        },
        "cross_filesystems": {
          "type": "boolean"
        }
      },
      "required": [
        "max_entries",
        "max_directory_entries",
        "max_depth",
        "max_seconds",
        "hash_files",
        "max_hash_file_bytes",
        "max_hash_total_bytes",
        "max_hash_files",
        "exclude_names",
        "cross_filesystems"
      ],
      "additionalProperties": false
    },
    "coverage": {
      "type": "object",
      "properties": {
        "entries_observed": {
          "type": "integer",
          "minimum": 0
        },
        "status_counts": {
          "type": "object",
          "additionalProperties": {
            "type": "integer",
            "minimum": 0
          }
        },
        "hashed_files": {
          "type": "integer",
          "minimum": 0
        },
        "hashed_bytes": {
          "type": "integer",
          "minimum": 0
        },
        "hash_status_counts": {
          "type": "object",
          "additionalProperties": {
            "type": "integer",
            "minimum": 0
          }
        },
        "stop_reason": {
          "enum": [
            null,
            "cancelled",
            "time_limit",
            "entry_limit",
            "exclusion_limit"
          ]
        },
        "atomic_snapshot": {
          "const": false
        },
        "complete_within_policy": {
          "type": "boolean"
        },
        "hash_attempts": {
          "type": "integer",
          "minimum": 0
        }
      },
      "required": [
        "entries_observed",
        "status_counts",
        "hashed_files",
        "hashed_bytes",
        "hash_status_counts",
        "stop_reason",
        "atomic_snapshot",
        "complete_within_policy",
        "hash_attempts"
      ],
      "additionalProperties": false
    },
    "scan": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "started_at": {
          "type": "string",
          "format": "date-time"
        },
        "roots": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128
              },
              "path": {
                "type": "string"
              },
              "status": {
                "enum": [
                  "pending",
                  "unvisited",
                  "observed",
                  "stale",
                  "unreadable",
                  "disappeared",
                  "unsupported"
                ]
              },
              "identity": {
                "$ref": "#/$defs/fingerprint"
              }
            },
            "required": [
              "id",
              "path",
              "status",
              "identity"
            ],
            "additionalProperties": false
          },
          "maxItems": 16
        },
        "status": {
          "enum": [
            "complete",
            "partial",
            "cancelled"
          ]
        },
        "limits": {
          "$ref": "#/$defs/limits"
        },
        "coverage": {
          "$ref": "#/$defs/coverage"
        },
        "hash_policy": {
          "enum": [
            "bounded_sha256",
            "metadata_only"
          ]
        },
        "errors": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "entry_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128
              },
              "kind": {
                "type": "string"
              },
              "errno": {
                "type": [
                  "integer",
                  "null"
                ],
                "minimum": 0
              }
            },
            "required": [
              "entry_id",
              "kind",
              "errno"
            ],
            "additionalProperties": false
          },
          "maxItems": 100000
        },
        "exclusions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "entry_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128
              },
              "reason": {
                "type": "string"
              }
            },
            "required": [
              "entry_id",
              "reason"
            ],
            "additionalProperties": false
          },
          "maxItems": 100000
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "id",
        "started_at",
        "roots",
        "status",
        "limits",
        "coverage",
        "hash_policy",
        "errors",
        "exclusions",
        "uncertainties"
      ],
      "additionalProperties": false
    },
    "evidence": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "kind": {
          "type": "string"
        },
        "member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "observations": {
          "type": "object"
        },
        "confidence": {
          "const": "observed"
        }
      },
      "required": [
        "id",
        "kind",
        "member_ids",
        "observations",
        "confidence"
      ],
      "additionalProperties": false
    },
    "relationship": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "kind": {
          "type": "string"
        },
        "member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "confidence": {
          "enum": [
            "observed",
            "hypothesis",
            "unknown"
          ]
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "id",
        "kind",
        "member_ids",
        "evidence_ids",
        "confidence",
        "uncertainties"
      ],
      "additionalProperties": false
    },
    "finding": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "kind": {
          "type": "string"
        },
        "member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "confidence": {
          "enum": [
            "observed",
            "hypothesis",
            "unknown"
          ]
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "title": {
          "type": "string"
        },
        "counter_evidence": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "id",
        "kind",
        "member_ids",
        "evidence_ids",
        "confidence",
        "uncertainties",
        "title",
        "counter_evidence"
      ],
      "additionalProperties": false
    },
    "directory": {
      "type": "object",
      "properties": {
        "entry_id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "direct_member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "logical_bytes": {
          "type": "integer",
          "minimum": 0
        },
        "observed_files": {
          "type": "integer",
          "minimum": 0
        },
        "uncertain_entries": {
          "type": "integer",
          "minimum": 0
        },
        "role_hypotheses": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "role": {
                "enum": [
                  "project",
                  "archive",
                  "inbox",
                  "cache"
                ]
              },
              "confidence": {
                "const": "hypothesis"
              },
              "evidence_ids": {
                "type": "array",
                "items": {
                  "type": "string",
                  "minLength": 1,
                  "maxLength": 128
                },
                "maxItems": 100000
              }
            },
            "required": [
              "role",
              "confidence",
              "evidence_ids"
            ],
            "additionalProperties": false
          },
          "maxItems": 4
        },
        "confidence": {
          "enum": [
            "observed",
            "hypothesis",
            "unknown"
          ]
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "coverage": {
          "type": "object",
          "properties": {
            "complete": {
              "type": "boolean"
            },
            "reasons": {
              "type": "array",
              "items": {
                "type": "string"
              }
            }
          },
          "required": [
            "complete",
            "reasons"
          ],
          "additionalProperties": false
        }
      },
      "required": [
        "entry_id",
        "direct_member_ids",
        "logical_bytes",
        "observed_files",
        "uncertain_entries",
        "role_hypotheses",
        "confidence",
        "uncertainties",
        "coverage"
      ],
      "additionalProperties": false
    },
    "aggregates": {
      "type": "object",
      "properties": {
        "logical_bytes_by_path": {
          "type": "integer",
          "minimum": 0
        },
        "logical_bytes_by_observed_object": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "known_allocated_bytes_by_observed_object": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "allocation_unknown_objects": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "physical_bytes": {
          "const": null
        },
        "recoverable_bytes": {
          "const": null
        },
        "observed_regular_files": {
          "type": "integer",
          "minimum": 0
        },
        "distinct_observed_file_objects": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "hard_link_alias_paths": {
          "type": [
            "integer",
            "null"
          ],
          "minimum": 0
        },
        "status_counts": {
          "type": "object",
          "additionalProperties": {
            "type": "integer",
            "minimum": 0
          }
        },
        "by_extension_category": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "entry_count": {
                "type": "integer",
                "minimum": 0
              },
              "logical_bytes": {
                "type": "integer",
                "minimum": 0
              }
            },
            "required": [
              "entry_count",
              "logical_bytes"
            ],
            "additionalProperties": false
          }
        },
        "partial": {
          "type": "boolean"
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "object_identity_unknown_paths": {
          "type": "integer",
          "minimum": 0
        }
      },
      "required": [
        "logical_bytes_by_path",
        "logical_bytes_by_observed_object",
        "known_allocated_bytes_by_observed_object",
        "allocation_unknown_objects",
        "physical_bytes",
        "recoverable_bytes",
        "observed_regular_files",
        "distinct_observed_file_objects",
        "hard_link_alias_paths",
        "status_counts",
        "by_extension_category",
        "partial",
        "uncertainties",
        "object_identity_unknown_paths"
      ],
      "additionalProperties": false
    },
    "step": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "type": {
          "enum": [
            "keep_unchanged",
            "inspect_evidence",
            "ask_about_intent"
          ]
        },
        "member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "depends_on": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        }
      },
      "required": [
        "id",
        "type",
        "member_ids",
        "depends_on",
        "evidence_ids"
      ],
      "additionalProperties": false
    },
    "alternative": {
      "type": "object",
      "properties": {
        "id": {
          "enum": [
            "keep_current_structure",
            "review_grouping"
          ]
        },
        "label": {
          "type": "string"
        },
        "steps": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/step"
          },
          "maxItems": 2
        },
        "expected_consequences": {
          "type": "object",
          "properties": {
            "filesystem_changes": {
              "const": 0
            },
            "additional_content_reads": {
              "const": 0
            }
          },
          "required": [
            "filesystem_changes",
            "additional_content_reads"
          ],
          "additionalProperties": false
        },
        "unchanged_member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "uncertain_member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        }
      },
      "required": [
        "id",
        "label",
        "steps",
        "expected_consequences",
        "unchanged_member_ids",
        "uncertain_member_ids"
      ],
      "additionalProperties": false
    },
    "plan": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 128
        },
        "kind": {
          "const": "read_only_review_alternatives"
        },
        "finding_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "scope_member_ids": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "executable": {
          "const": false
        },
        "alternatives": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/alternative"
          },
          "maxItems": 2
        },
        "reasons": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "outside_scope": {
          "type": "string"
        }
      },
      "required": [
        "id",
        "kind",
        "finding_ids",
        "scope_member_ids",
        "executable",
        "alternatives",
        "reasons",
        "uncertainties",
        "outside_scope"
      ],
      "additionalProperties": false
    },
    "changes": {
      "type": "object",
      "properties": {
        "previous_scan_id": {
          "type": [
            "string",
            "null"
          ]
        },
        "comparable": {
          "type": "boolean"
        },
        "added": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "changed": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "unchanged_metadata": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "no_longer_observed": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "unverified_absent": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
          },
          "maxItems": 100000
        },
        "hashes_reused": {
          "const": 0
        },
        "uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "previous_scan_id",
        "comparable",
        "added",
        "changed",
        "unchanged_metadata",
        "no_longer_observed",
        "unverified_absent",
        "hashes_reused",
        "uncertainties"
      ],
      "additionalProperties": false
    }
  }
}
''')


def _matches_type(value, expected):
    choices = expected if isinstance(expected, list) else [expected]
    kinds = {"null": value is None, "boolean": type(value) is bool,
             "integer": type(value) is int, "number": type(value) in (int, float),
             "string": isinstance(value, str), "array": isinstance(value, list),
             "object": isinstance(value, dict)}
    return any(kinds[name] for name in choices)


def _validate(value, schema, path):
    if "$ref" in schema:
        return _validate(value, SCHEMA["$defs"][schema["$ref"].split("/")[-1]], path)
    if "anyOf" in schema:
        for alternative in schema["anyOf"]:
            try:
                _validate(value, alternative, path)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"{path}: no allowed type matches")
    for rule in schema.get("allOf", []):
        _validate(value, rule, path)
    if "if" in schema:
        try:
            _validate(value, schema["if"], path)
            branch = "then"
        except ValueError:
            branch = "else"
        _validate(value, schema.get(branch, {}), path)
    if "type" in schema and not _matches_type(value, schema["type"]):
        raise ValueError(f"{path}: invalid type")
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        raise ValueError(f"{path}: invalid category")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ValueError(f"{path}: fixed contract value differs")
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: non-finite number")
        if ("minimum" in schema and value < schema["minimum"]
                or "maximum" in schema and value > schema["maximum"]
                or "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]):
            raise ValueError(f"{path}: number outside bounds")
    if isinstance(value, str):
        if schema.get("format") == "date-time":
            if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError(f"{path}: timestamp requires a timezone")
        if (len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 2**31)
                or "pattern" in schema and not re.search(schema["pattern"], value)):
            raise ValueError(f"{path}: string outside contract")
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 2**31):
            raise ValueError(f"{path}: array outside bounds")
        for index, child in enumerate(value):
            _validate(child, schema.get("items", {}), f"{path}[{index}]")
    if isinstance(value, dict):
        if any(key not in value for key in schema.get("required", [])):
            raise ValueError(f"{path}: required fields missing")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                _validate(child, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise ValueError(f"{path}: unexpected field")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate(child, schema["additionalProperties"], f"{path}.{key}")


def validate_contract(value):
    """Check the complete fixed shape before any imported contract is exposed."""
    try:
        # Enforce JSON-only values, finite numbers and acyclic data even in open
        # evidence.observations fields. No content or filesystem read occurs.
        json.dumps(value, allow_nan=False)
        _validate(value, SCHEMA, "inventory")
    except (TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("Inventory is not bounded JSON-compatible data") from exc
