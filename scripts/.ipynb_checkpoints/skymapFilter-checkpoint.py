#!/usr/bin/env python3
import healpy as hp
import argparse
import os
import tempfile
import numpy as np
from ligo.gracedb.rest import GraceDb
from ligo.skymap.io import read_sky_map
from ligo.skymap.postprocess.contour import contour

def process_superevent(gdb, superevent_id, area_limit=300):
    """Return True if superevent has a skymap with area_90 < area_limit."""
    if superevent_id.startswith("M"):
        return False
    try:
        # Get superevent JSON
        se = gdb.superevent(superevent_id).json()
        se_id = se['superevent_id']
        # preferred = se.get("pipeline_preferred_events")
        # preferred = preferred[list(preferred.keys())[0]]["graceid"]
        # if not preferred:
        #     return False

        # # List files attached to preferred event
        # files = gdb.files(preferred).json()
        # fits_files = [f for f in files if f.endswith(".fits") or f.endswith(".fits.gz")]
        # if not fits_files:
        #     return False

        # Take first skymap file (can refine if needed)
        # fname = fits_files[0]
        # response = client.files(preferred, 'skymap.fits.gz')
        # file_contents = response.read()
        # print(fname)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            data = gdb.files(se_id, 'bayestar.fits.gz').read()
            tmp.write(data)
            tmp_path = tmp.name

        # Read skymap and compute contour areas
        prob, _ = read_sky_map(tmp_path)
        sorted_probs = np.flipud(np.sort(prob))
        levels = np.cumsum(sorted_probs)
        index90 = np.searchsorted(levels, 0.90) 
# areas = contour(prob)
        os.remove(tmp_path)
        area_90 = index90*hp.nside2pixarea(hp.get_nside(prob),degrees=True)
        return area_90 < area_limit

    except Exception as e:
        print(f"Skipping {superevent_id}: {e}")
        return False

def main(input_file, output_file, area_limit=300):
    gdb = GraceDb()  # no token needed for public events

    with open(input_file, "r") as f:
        superevents = [line.strip() for line in f if line.strip()]

    kept = []
    for se_id in superevents[::-1]:
        print(f"Checking {se_id}...")
        if process_superevent(gdb, se_id, area_limit=area_limit):
            print(f"Superevent {se_id} passes {area_limit} deg^2 area criterion")
            kept.append(se_id)

    with open(output_file, "w") as f:
        for se_id in kept:
            f.write(se_id + "\n")

    print(f"Done. Wrote {len(kept)} superevent IDs to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter superevents by 90% area < 300 deg²")
    parser.add_argument("input_file", help="Text file with one superevent ID per line")
    parser.add_argument("output_file", help="Text file to write filtered superevent IDs")
    parser.add_argument("--area-limit", type=float, default=300, help="Area threshold in deg²")
    args = parser.parse_args()

    main(args.input_file, args.output_file, area_limit=args.area_limit)
