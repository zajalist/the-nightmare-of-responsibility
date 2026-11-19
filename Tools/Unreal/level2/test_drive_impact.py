"""Bounded city impact/re-formation curve and actual graph ownership checks."""
import build_drive as b
import drive_data as d
assert [d.impact_progress(t) for t in (-1,0,.25,3,10)] == [0,0,1,0,0]
assert 0 < d.impact_progress(1.5) < 1
plans=[]
b.inspect=lambda path,name:([dict(node_id='entry',title=name)],[])
b.G.run=lambda self:plans.append(self)
for name in ('BP_Meteor.Step','BP_Meteor.Impact','BP_Meteor.UpdateImpact','BP_Meteor.ResetImpact','BP_L2Car.Deactivate'):
    b.STEPS[name]()
by_name={p.graph:p for p in plans}
def calls(name):return [o.get('function_name','') for o in by_name[name].ops]
assert any(x.endswith(':UpdateImpact') for x in calls('Step'))
assert any(x.endswith(':ResetImpact') for x in calls('Deactivate'))
for param in ('SandCentre','SandProgress','SandRadius'):
    assert any(o.get('value')==param for o in by_name['UpdateImpact'].ops)
    assert not any(o.get('value')==param for o in by_name['Impact'].ops)
assert any(o.get('value')=='SandRadius' for o in by_name['Deactivate'].ops)
assert not any(o.get('value') in ('SandProgress','SandRadius') for o in by_name['ResetImpact'].ops)
assert any(o.get('value')=='Impact0' for o in by_name['Impact'].ops)
assert any(o.get('value')=='Impact0' for o in by_name['ResetImpact'].ops)
assert any(o.get('value')=='-10000' and o.get('pin_name')=='B' for o in by_name['ResetImpact'].ops)
assert any(o.get('value')=='0' and o.get('pin_name')=='A' for o in by_name['ResetImpact'].ops)
assert any(float(o['value'])==d.SHOCKWAVE_DURATION for o in by_name['UpdateImpact'].ops
           if o.get('op')=='set_pin' and o.get('pin_name')=='B')
assert not any('BP_FoAPlayer' in x for x in calls('UpdateImpact'))
print('City impact checks passed: expanding sand, separate shockwave expiry, independent hero state, cleanup')
