"""Emit synthetic reviews to stdout. No scans, files, providers or mutations."""

import json

from fixtures import blocked_example, sample_document
from planning_preview import review


if __name__ == "__main__":
    print(json.dumps({"blocked_example": review(blocked_example()),
                      "reviewable_fixture": review(sample_document())}, indent=2))
