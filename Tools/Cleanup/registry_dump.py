"""READ-ONLY: dump the AssetRegistry graph for /Game into Saved/Cleanup/registry/chunk_<i>.json.

  $env:FOA_AGENT='cleanup'; python Tools/Unreal/integration/run_read.py Tools/Cleanup/registry_dump.py FOA_CHUNK=0 FOA_NCHUNKS=4

One record per package: classes, hard and soft package dependencies, and the registry tags the audit needs
(texture dimensions/format/compression, mesh size). Loads no asset and writes nothing under Content.
"""
import json
import os
import time

import unreal

TAGS = ("Dimensions", "Format", "CompressionSettings", "LODGroup", "MaxTextureSize", "SRGB", "NeverStream",
        "HasAlphaChannel", "MipGenSettings", "SourceCompression", "ApproxSize", "Triangles", "Vertices", "Duration",
        "ParentClass", "Parent", "AssetImportData")


def main():
    t0 = time.time()
    i, n = int(os.environ.get("FOA_CHUNK", "0")), int(os.environ.get("FOA_NCHUNKS", "1"))
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path("/Game", recursive=True, include_only_on_disk_assets=False)
    by_pkg = {}
    for ad in assets:
        by_pkg.setdefault(str(ad.package_name), []).append(ad)
    pkgs = sorted(by_pkg)[i::n]
    hard = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False,
                                                 include_hard_package_references=True, include_searchable_names=False,
                                                 include_soft_management_references=False,
                                                 include_hard_management_references=False)
    soft = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=False, include_searchable_names=False,
                                                 include_soft_management_references=False,
                                                 include_hard_management_references=False)
    out = {}
    for p in pkgs:
        rec = {"assets": []}
        for ad in by_pkg[p]:
            tags = {}
            for t in TAGS:
                v = ad.get_tag_value(t)
                if isinstance(v, tuple):  # (found, value) on some builds
                    v = v[1] if v[0] else None
                if v:
                    tags[t] = str(v)
            rec["assets"].append({"name": str(ad.asset_name), "class": str(ad.asset_class_path.asset_name),
                                  "class_pkg": str(ad.asset_class_path.package_name), "tags": tags})
        rec["hard"] = sorted({str(d) for d in (ar.get_dependencies(p, hard) or [])})
        rec["soft"] = sorted({str(d) for d in (ar.get_dependencies(p, soft) or [])} - set(rec["hard"]))
        out[p] = rec
    path = os.path.join(unreal.Paths.project_saved_dir(), "Cleanup", "registry", f"chunk_{i}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"chunk": i, "nchunks": n, "total_packages": len(by_pkg), "packages": out}, fh)
    print(f"registry_dump chunk {i}/{n}: {len(pkgs)} of {len(by_pkg)} packages in {time.time() - t0:.1f}s -> {path}")


main()
