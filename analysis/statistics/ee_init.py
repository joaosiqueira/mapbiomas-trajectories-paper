"""Earth Engine initialisation for the scripts in this folder.

Call `initialize()` before any other `ee` call. Run `earthengine authenticate` once
beforehand. The Cloud project is read from the EE_PROJECT environment variable:

    EE_PROJECT=my-gcp-project python mapbiomas_brazil_annual_events_to_asset.py --dry-run

Without it, `ee.Initialize` falls back to the project of the stored credential.
"""
import os

import ee


def initialize():
    project = os.environ.get('EE_PROJECT')

    if project:
        ee.Initialize(project=project)
    else:
        ee.Initialize()

    return project
