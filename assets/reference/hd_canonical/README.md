# Wizard Joe HD Alpha Authority

The user-supplied production alpha archives are the source authority for the HD
Wizard Joe actor. The earlier staff-redesign and image-regeneration experiments
are superseded and must not be used to alter these frames.

The 250-frame production package is approved as transparent source art. The
ten-frame forward-camera flight package remains a review candidate until its
animation gate is accepted. Runtime rendering uses the compiled `.wjpose`
colored-pixel artifacts under `compiled/`; PNG files are never runtime render
assets.

Rebuild with:

```bash
python3 tools/build_hd_pose_masters.py \
  --production-archive "/path/to/Wizard_Joe_Production_Alpha_Set_001_250_v001.zip" \
  --flight-archive "/path/to/Wizard_Joe_Forward_Camera_Flight_Alpha_Cycle_v001 (1).zip"
```

The compiler verifies both archive hashes, every per-frame source hash, the
RGBA canvas contract, transparent corners, frame counts, category coverage,
and approval state before writing artifacts.
