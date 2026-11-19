"""Keys of Curve_GameplayExposure (BP_ViewFill.GameplayExposure's AutoExposureBiasCurve): scene EV100 -> exposure
compensation in stops. Full lift below -5.5 (T3, T4, T7, the look-down), none from -3.3 up (yaw 195, the bay), so the
EV100 floor of -2.8 only opens dark gameplay views. FloatCurve is not Python-editable, so this writes it through Hayba.
  python Tools/Splats/view_fill_curve.py      (after build_view_fill.py FOA_FILL=assets has created the asset)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

CURVE = '/Game/FoA/Gameplay/Ambient/Curve_GameplayExposure'
KEYS = ((-10.0, 0.0), (-5.5, 0.0), (-3.3, -1.8), (-2.8, -1.8), (-1.0, 0.0), (6.0, 0.0))   # plateau = EXPOSURE_MIN + 1

obj = CURVE + '.' + CURVE.rsplit('/', 1)[1]
text = '(Keys=(' + ','.join(f'(InterpMode=RCIM_Linear,Time={t:.6f},Value={v:.6f})' for t, v in KEYS) + '))'
lease = h.lease_acquire(h.agent_id(), ['asset:' + CURVE], ttl_s=60, wait_s=120)
try:
    r = h.call('object_set_property', dict(path=obj, properties={'FloatCurve': text}))
    assert (r.get('data') or {}).get('applied') == ['FloatCurve'], r
    assert h.call('asset_save', dict(asset_paths=[CURVE])).get('ok')
    back = str((h.call('object_get_property', dict(path=obj, names=['FloatCurve'])).get('data') or {}).get('properties'))
    assert back.count('Time=') == len(KEYS), back
    print('curve ok', back[:300])
finally:
    h.release(h.agent_id(), lease)
