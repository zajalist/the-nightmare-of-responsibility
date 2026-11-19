"""Small builder over unreal.MaterialEditingLibrary for lean, commented material / material-function graphs.
exec(open('P:/FoA/Tools/Unreal/ui/mat_graph.py').read()) from a script run by Tools/Unreal/ue_remote.py.
Builders clear the asset's graph first, so reruns are idempotent."""
import unreal

MEL = unreal.MaterialEditingLibrary
# One colour per functional group, shared by every UI material so graphs read alike.
COL = {
    "input": unreal.LinearColor(0.10, 0.20, 0.35, 1),
    "shape": unreal.LinearColor(0.12, 0.26, 0.16, 1),
    "noise": unreal.LinearColor(0.30, 0.22, 0.10, 1),
    "fx": unreal.LinearColor(0.32, 0.12, 0.10, 1),
    "out": unreal.LinearColor(0.22, 0.22, 0.22, 1),
}


class MatGraph:
    def __init__(self, path, function=False):
        self.asset = unreal.load_asset(path)
        assert self.asset, path
        # Crash safety: never mutate a graph that is open in its asset editor.
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(self.asset)
        self.fn = function
        self.path = path
        self.comment_sizes = []

    def clear(self):
        # delete_all_* skips nodes (it mutates the array it walks), so delete from a snapshot and verify.
        if self.fn:
            for e in list(MEL.get_material_function_expressions(self.asset)):
                MEL.delete_material_expression_in_function(self.asset, e)
            left = MEL.get_num_material_expressions_in_function(self.asset)
        else:
            for e in list(MEL.get_material_expressions(self.asset)):
                MEL.delete_material_expression(self.asset, e)
            left = MEL.get_num_material_expressions(self.asset)
        assert left == 0, f"{self.path}: {left} expressions survived clear()"
        return self

    def add(self, cls, x, y, **props):
        cls = getattr(unreal, cls) if isinstance(cls, str) else cls
        if self.fn:
            e = MEL.create_material_expression_in_function(self.asset, cls, x, y)
        else:
            e = MEL.create_material_expression(self.asset, cls, x, y)
        assert e, cls
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def param(self, cls, name, x, y, group, value, priority=0, desc=""):
        e = self.add(cls, x, y, parameter_name=name, group=group, sort_priority=priority)
        e.set_editor_property("default_value", value)
        if desc:
            e.set_editor_property("desc", desc)
        return e

    def call(self, function_path, x, y):
        e = self.add("MaterialExpressionMaterialFunctionCall", x, y)
        e.set_material_function(unreal.load_asset(function_path))
        return e

    def link(self, a, a_out, b, b_in):
        ok = MEL.connect_material_expressions(a, a_out, b, b_in)
        assert ok, f"link {a.get_name()}.{a_out!r} -> {b.get_name()}.{b_in!r}"

    def out(self, a, a_out, prop):
        ok = MEL.connect_material_property(a, a_out, prop)
        assert ok, f"out {a.get_name()}.{a_out!r} -> {prop}"

    def comment(self, title, desc, x, y, w, h, group):
        """House style: title + one-line why, coloured bubble shown when zoomed out."""
        c = self.add("MaterialExpressionComment", x, y)
        # SizeX/SizeY are not script-visible: sizes are applied afterwards with Hayba material_set_comment.
        self.comment_sizes.append((f"{title}", x, y, w, h))
        for k, v in (("text", f"{title}\n{desc}"), ("comment_color", COL[group]),
                     ("font_size", 18), ("comment_bubble_visible_in_details_panel", True),
                     ("color_comment_bubble", True)):
            c.set_editor_property(k, v)
        return c

    def finish(self):
        import json
        print("COMMENT_SIZES", self.path, json.dumps(self.comment_sizes))
        if self.fn:
            MEL.update_material_function(self.asset, None)
        else:
            MEL.recompile_material(self.asset)
        unreal.EditorAssetLibrary.save_loaded_asset(self.asset, False)
        if self.fn:
            print("saved", self.path, "nodes:", MEL.get_num_material_expressions_in_function(self.asset))
        else:
            st = MEL.get_statistics(self.asset)
            print("saved", self.path, "nodes:", MEL.get_num_material_expressions(self.asset),
                  "| PS instructions:", st.num_pixel_shader_instructions, "| VS:", st.num_vertex_shader_instructions,
                  "| samplers:", st.num_samplers)
