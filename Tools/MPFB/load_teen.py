"""Load the user's MakeHuman model (read fresh every build, never written) into MPFB, game-ready settings.
  from load_teen import load_teen; body, rig = load_teen()"""
import os

import bpy

from mpfb_common import mpfb

MHM = "P:/FoA-Assets/character/makehuman_home/makehuman/v1py3/models/foa_teen.mhm"


def load_teen(path=MHM):
    HumanService = mpfb("services.humanservice", "HumanService")
    ObjectService = mpfb("services.objectservice", "ObjectService")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    bpy.ops.wm.read_homefile(use_empty=True)
    settings = dict(HumanService.get_default_deserialization_settings(),
                    subdiv_levels=0,                   # game mesh: no subdivision anywhere
                    override_skin_model="GAMEENGINE",  # one plain base-colour skin, swappable later
                    clothes_deep_search=True, bodypart_deep_search=True)  # resolve the MHM's asset UUIDs
    body = HumanService.deserialize_from_mhm(path, settings)
    rig = ObjectService.find_object_of_type_amongst_nearest_relatives(body, "Skeleton")
    if rig is None:
        raise RuntimeError("the MHM has no skeleton line; the game needs game_engine")
    return body, rig
