"""One editor run: set the moon-bounce light to FOA_LM lumens, then capture the two judging views through the dream PP.
  $env:FOA_ACTORS_NEW='Light_MoonBounce_Fireplace,TMP_fireplace_'; ue_remote.py Tools/Fireplace/fp_light_check.py FOA_LM=12 FOA_TAG=lit12
Writes Saved/FireplaceShots/v2_close_<tag>.png and v2_wide_fp_<tag>.png (fp_capture.py, a TMP actor destroyed per shot)."""
import os
import runpy

HERE = "P:/FoA/Tools/Fireplace/"
tag = os.environ.get("FOA_TAG", "lit")
runpy.run_path(HERE + "place_fireplace_light.py", run_name="__main__")
for name, cam, look in (("v2_close_" + tag, "-130,-80,165", "-330,0,75"), ("v2_wide_fp_" + tag, "-340,280,270", "-330,0,90"),
                        ("v2_wide_room_" + tag, "120,-170,190", "-330,0,85")):  # across the room: nothing in the way
    os.environ.update(FOA_NAME=name, FOA_CAM=cam, FOA_LOOK=look, FOA_FOV="70", FOA_PPMAT="1")
    runpy.run_path(HERE + "fp_capture.py", run_name="__main__")
for k in ("FOA_NAME", "FOA_CAM", "FOA_LOOK", "FOA_FOV", "FOA_PPMAT"):
    os.environ.pop(k, None)
