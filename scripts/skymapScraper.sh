#!/usr/bin/env python3
import os
from ligo.gracedb.rest import GraceDb
import healpy as hp
from ligo.skymap.io import read_sky_map
from ligo.skymap.postprocess.contour import contour

# Connect to GraceDB (no authentication needed for public events)
client = GraceDb()

# Directory to save filtered skymaps
OUTDIR = "small_area_skymaps"
os.makedirs(OUTDIR, exist_ok=True)


superevent_iterator = client.superevents('public is_gw: True')
events = [superevent['superevent_id'] for superevent in superevent_iterator]
## Get all superevents (not just O4)
#all_events = []
#for page in client.superevents("superevent_catalog"):
#    all_events.extend(page['superevents'])
#events = all_events
#

print(events)
print(f"Found {len(events)} superevents")

for se in events:
    se_id = se['superevent_id']

    try:
        # Get preferred event
        preferred = client.superevent(se_id).json().get('preferred_event')
        if not preferred:
            continue

        # List files
        files = client.files(preferred).json()
        # Look for a sky map FITS file
        skymap_files = [f for f in files if f.endswith(".fits")]

        if not skymap_files:
            continue

        # Use the first skymap file (could refine)
        skymap_url = files[skymap_files[0]]
        skymap_data = client.files(preferred, skymap_files[0])

        # Save temporarily
        tmpfile = f"/tmp/{skymap_files[0]}"
        with open(tmpfile, "wb") as f:
            f.write(skymap_data.read())

        # Read skymap
        prob, meta = read_sky_map(tmpfile, map_units='prob')

        # Compute areas of credible regions
        areas = contour(prob)
        area_90 = areas[0.9]

        if area_90 < 300:  # square degrees
            outpath = os.path.join(OUTDIR, skymap_files[0])
            os.rename(tmpfile, outpath)
            print(f"{se_id}: saved skymap (90% area = {area_90:.1f} deg²)")
        else:
            os.remove(tmpfile)

    except Exception as e:
        print(f"Skipping {se_id}: {e}")
