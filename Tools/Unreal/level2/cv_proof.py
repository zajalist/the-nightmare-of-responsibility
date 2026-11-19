"""Bounded child driver for the parent's isolated QA PIE. Import has no engine effects.

driver = create_cv_proof(world, journey, cap_seconds=35)
driver.tick(dt) on the parent's existing callback; read driver.done/result/state.
Always driver.close() in the parent's finally, before ending PIE. No callback,
PIE lifecycle, save isolation, asset writes or direct battle-state assignments here.

The first defeat is an OUTCOME CONTRACT fixture: authored damage via ApplySelf,
then real Flee/CheckEnd. The retry is ACTUAL ACTION play: ChooseMove/CycleTarget,
with no health, resolve, progress, intents or Remaining overrides. Time is accelerated.
This is native API play, not keyboard/controller or visual-quality evidence.
"""
import math
import time

from cv_data import MOVES as CV_MOVES, DATA
from encounter_data import MOVES as L1_MOVES

MOVES = dict(L1_MOVES, **CV_MOVES)
FLAGS = ('Knows.L2Experience', 'Knows.L2Logistics', 'Knows.L2Reliability')


def predict(s, target, move):
    """One-turn policy estimate; only actual Blueprint callbacks provide proof."""
    m = MOVES[move]
    st = set(s['statuses'])
    cost = 0 if m['bRevealsNext'] and s.get('free_preview') else m['ResolveCost']
    if cost > s['resolve'] or m['BlockedBy'] in st:
        return None
    c = min(100, max(0, s['composure'] + m['ComposureDelta']))
    r = min(40, max(0, s['resolve'] - cost + m['ResolveDelta']))
    st.discard(m['StatusCleared'])
    if m['StatusApplied']:
        st.add(m['StatusApplied'])
    progress = [g['progress'] for g in s['sections']]
    if target is not None:
        progress[target] = min(4, max(0, progress[target] + m['ProgressDelta']))
    if all(p == 4 for p in progress):
        return 1e6
    for i, section in enumerate(s['sections']):
        if progress[i] == 4 or section['state'] == 'Stunned' or (i == target and m['bStuns']):
            continue
        enemy = MOVES.get(section['intent'], CV_MOVES['CVWait'])
        c = max(0, c + enemy['ComposureDelta'])
        r = min(40, max(0, r + enemy['ResolveDelta']))
        progress[i] = min(4, max(0, progress[i] + enemy['ProgressDelta']))
        if enemy['StatusApplied']:
            st.add(enemy['StatusApplied'])
    c = max(0, c - 2)
    if c == 0:
        return -10000
    # Completed sections cease attacking. Prioritize finishing one, then survival.
    score = 90 * progress.count(4) + 12 * sum(progress)
    score += 40 * math.log1p(c / 20) + 10 * math.log1p(r / 10)
    score -= sum(7 if x == 'Constricted' else 3 for x in st if x != 'ArmholeFound')
    if 'Constricted' in st and any(g['id'] == 'CVReliability' and progress[i] == 4
                                  for i, g in enumerate(s['sections'])):
        score -= 100  # Avoid losing the only action that can restore Breathe.
    return score


def choose_action(s):
    candidates = [(None, 'DeepBreath'), (None, 'CheckMirror')]
    candidates += [(i, move) for i, g in enumerate(s['sections'])
                   if g['progress'] < 4 for move in g['actions']
                   if move != 'CVFindDetail' or 'SleeveLabyrinth' in s['statuses']]
    legal = [(predict(s, i, m), i, m) for i, m in candidates]
    legal = [x for x in legal if x[0] is not None]
    assert legal, 'No legal battle action'
    _, target, move = max(legal, key=lambda x: x[0])
    return target, move


class CVProof:
    def __init__(self, world, journey, cap_seconds=35, speed=12, engine=None, now=None):
        if engine is None:
            import unreal as engine
        self.u, self.world, self.journey = engine, world, journey
        self.now = now or time.monotonic
        self.started = self.now()
        self.cap, self.speed = min(35., max(1., cap_seconds)), speed
        self.done, self.state, self.acted = False, 'start', False
        self.encounter = self.player = self.gi = None
        self.original_speed = 1.
        self.result = dict(passed=False, outcome_contract={}, actual_actions={}, trace=[],
                           scope='Native API actions; forced defeat is a separate outcome fixture')
        assert self.alive(), 'Live parent-owned QA PIE required'
        self.gi = engine.GameplayStatics.get_game_instance(world)
        assert self.valid(self.gi) and str(self.get(self.gi, 'SaveSlot')) == 'FoA_QA_Play', 'Isolate QA save first'
        self.player = self.get(journey, 'Player')
        self.encounter = self.get(journey, 'Encounter')
        assert self.valid(self.player) and self.valid(self.encounter), 'Journey actor references required'
        assert self.get(journey, 'Phase') == 11 and self.get(journey, 'Employability') == 60
        assert all(self.get(journey, 'Edited' + str(i)) for i in range(3)), 'Confirm three real stops first'
        self.baseline = self.persistent()
        assert set(FLAGS) <= set(self.baseline['knowledge']), 'Stop notes absent'
        self.clothing = self.clothes()
        self.original_speed = engine.GameplayStatics.get_global_time_dilation(world)

    @staticmethod
    def get(obj, field):
        return obj.get_editor_property(field)

    def valid(self, obj):
        return obj is not None and self.u.SystemLibrary.is_valid(obj)

    def alive(self):
        if not self.valid(self.world) or not self.valid(self.journey):
            return False
        current = self.u.get_editor_subsystem(self.u.UnrealEditorSubsystem).get_game_world()
        return current == self.world and self.journey.get_world() == self.world

    def persistent(self):
        return dict(day=int(self.get(self.gi, 'DayCount')),
                    notes=[str(x) for x in self.get(self.gi, 'Notebook')],
                    knowledge=sorted(str(x) for x in self.get(self.gi, 'Knowledge')))

    def clothes(self):
        return {c.get_name():bool(c.is_visible()) for c in
                self.player.get_components_by_class(self.u.MeshComponent) if self.valid(c)}

    def snapshot(self):
        e = self.encounter
        sections = []
        for actor in self.get(e, 'Garments'):
            assert self.valid(actor), 'Invalid page actor'
            data, intent = self.get(actor, 'Data'), self.get(actor, 'Intent')
            assert self.valid(data), 'Invalid page data'
            assert str(self.get(data, 'GarmentId')) in ('', 'None'), 'CV row carries L1 clothing ID'
            assert actor.get_attach_parent_actor() != self.player, 'Page attached to player clothing'
            sections.append(dict(id=data.get_name().removeprefix('DA_Opponent_'),
                progress=int(self.get(actor, 'Progress')), state=str(self.get(actor, 'State')),
                intent=intent.get_name().removeprefix('DA_Move_') if self.valid(intent) else 'CVWait',
                actions=[x.get_name().removeprefix('DA_Move_') for x in self.get(data, 'ActMoves')]))
        return dict(composure=int(self.get(e, 'Composure')), resolve=int(self.get(e, 'Resolve')),
                    target=int(self.get(e, 'Target')), free_preview=bool(self.get(e, 'bFreePreview')),
                    statuses=[str(x) for x in self.get(e, 'Statuses')], sections=sections)

    def mark(self, label, **fields):
        self.result['trace'].append(dict(t=round(self.now()-self.started, 3), event=label, **fields))

    def finish(self, why, passed=False):
        if self.done:
            return
        self.result.update(passed=passed, reason=why, elapsed=round(self.now()-self.started, 3))
        self.done, self.state = True, 'done'
        self.close()

    def close(self):
        # Parent still owns Abort/PIE/save teardown. Never touch a replacement world.
        if self.alive():
            self.u.GameplayStatics.set_global_time_dilation(self.world, self.original_speed)

    def tick(self, _dt=0):
        if self.done:
            return
        try:
            if not self.alive() or not all(self.valid(x) for x in (self.encounter, self.player, self.gi)):
                return self.finish('pie_or_actor_gone')
            if self.now()-self.started > self.cap:
                return self.finish('cap')
            assert str(self.get(self.gi, 'SaveSlot')) == 'FoA_QA_Play', 'QA isolation changed'
            # Preserve authored hit-stop; restore acceleration after it ends.
            if self.u.GameplayStatics.get_global_time_dilation(self.world) > .5:
                self.u.GameplayStatics.set_global_time_dilation(self.world, self.speed)
            e, j = self.encounter, self.journey
            phase = int(self.get(j, 'Phase'))
            if self.state == 'start':
                j.call_method('Confirm', ())
                assert self.get(j, 'Phase') == 6 and self.get(e, 'bLevel2CV')
                self.mark('real_start_level2_cv')
                self.state = 'force_local_loss'
                return
            if self.state == 'force_local_loss':
                if not self.get(e, 'bPlayerTurn'):
                    return
                assert len(self.snapshot()['sections']) == 3
                damage = self.u.load_asset(DATA + '/DA_Move_CVOriginalReliability')
                assert self.valid(damage)
                for _ in range(9):
                    e.call_method('ApplySelf', (damage,))
                e.call_method('Flee', ())
                self.mark('forced_outcome_fixture', method='9 authored damage effects then Flee')
                self.state = 'wait_local_loss'
                return
            if self.state == 'wait_local_loss':
                if phase != 7:
                    return
                assert self.get(j, 'Employability') == 60 and not self.get(e, 'bActive')
                assert not self.get(e, 'bLevel2CV')
                assert self.persistent() == self.baseline, 'Loss changed L1 day or stop notes'
                assert self.clothes() == self.clothing, 'Loss changed clothing visibility'
                self.result['outcome_contract'] = dict(passed=True, day_unchanged=True,
                    notes_retained=True, employability=60, clothing_unchanged=True,
                    fixture='Forced loss via authored damage, not a played enemy defeat')
                j.call_method('Confirm', ())
                assert self.get(j, 'Phase') == 6 and not self.get(e, 'bCVAssisted')
                self.mark('real_normal_retry')
                self.state = 'normal_retry_loss_fixture'
                return
            if self.state == 'normal_retry_loss_fixture':
                if not self.get(e, 'bPlayerTurn'):
                    return
                assert not self.get(e, 'bCVAssisted'), 'Normal retry unexpectedly assists'
                damage = self.u.load_asset(DATA + '/DA_Move_CVOriginalReliability')
                assert self.valid(damage)
                for _ in range(9):
                    e.call_method('ApplySelf', (damage,))
                e.call_method('Flee', ())
                self.mark('second_outcome_fixture', method='9 authored damage effects then Flee')
                self.state = 'wait_assist_retry'
                return
            if self.state == 'wait_assist_retry':
                if phase != 7:
                    return
                assert self.get(j, 'Employability') == 60 and self.persistent() == self.baseline
                self.result['outcome_contract']['normal_retry_offered'] = True
                j.call_method('RetryWithoutTiming', ())
                assert self.get(j, 'Phase') == 6 and self.get(e, 'bCVAssisted')
                self.mark('real_optional_assisted_retry')
                self.state, self.acted = 'play_retry', False
                return
            if self.state == 'play_retry':
                if phase == 7:
                    self.result['actual_actions'].update(passed=False, result='defeat')
                    return self.finish('actual_action_defeat')
                if phase == 8:
                    assert self.get(j, 'Employability') == 100 and self.get(j, 'FinaleComplete')
                    assert not self.get(e, 'bActive') and not self.get(e, 'bLevel2CV')
                    assert self.persistent() == self.baseline, 'Win changed L1 day or stop notes'
                    # Visibility differences remain observable; merge presentation may legitimately change it.
                    self.result['actual_actions'].update(passed=True, result='victory', employability=100,
                        no_page_attached_to_player=True, no_garment_ids=True,
                        clothing_before=self.clothing, clothing_after=self.clothes())
                    self.mark('real_action_victory')
                    j.call_method('Confirm', ())
                    assert self.get(j, 'Submitted') and self.get(j, 'Phase') == 9
                    self.state = 'wait_ending'
                    return
                assert phase == 6, 'Unexpected journey phase during CV: ' + str(phase)
                if not self.get(e, 'bPlayerTurn'):
                    self.acted = False
                    return
                if self.acted:
                    return
                self.acted = True
                s = self.snapshot()
                assert len(s['sections']) == 3 and self.get(e, 'bCVAssisted')
                target, move = choose_action(s)
                if target is not None and target != s['target']:
                    e.call_method('CycleTarget', (target - s['target'],))
                    assert self.get(e, 'Target') == target, 'CycleTarget did not select expected section'
                path = DATA if move.startswith('CV') else '/Game/FoA/Gameplay/Encounter/Data'
                asset = self.u.load_asset(path + '/DA_Move_' + move)
                assert self.valid(asset), move
                e.call_method('ChooseMove', (asset,))
                self.result['actual_actions']['turns'] = self.result['actual_actions'].get('turns', 0) + 1
                self.mark('action', move=move, target=target, before=s)
                return
            if self.state == 'wait_ending':
                threshold = self.get(j, 'Threshold')
                assert self.valid(threshold)
                ending_phase = int(self.get(threshold, 'Phase'))
                assert ending_phase in (7, 8), 'Submit did not enter ending'
                if ending_phase == 8:
                    assert self.get(self.gi, 'DayCount') == self.baseline['day']
                    self.result['submission'] = dict(passed=True, journey_phase=9, threshold_phase=ending_phase)
                    self.mark('ending_colour_reveal')
                    return self.finish('passed', True)
        except Exception as exc:
            self.mark('error', message=str(exc), state=self.state)
            self.finish('error: ' + str(exc))


def create_cv_proof(world, journey, cap_seconds=35):
    return CVProof(world, journey, cap_seconds)
