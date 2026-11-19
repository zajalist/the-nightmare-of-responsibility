"""The bed-edge composite for the wake-up: seated hold, the snooze slap on the alarm clock (cfg["slap"]; the older
PickUp_Table reach without it), a breath, and standing up.
Mocap only (UAL Sitting_Idle_Loop, PickUp_Table, Sitting_Exit); nothing is hand-keyed. Three layers on top:
  - spine: PickUp_Table's spine motion as a local-space additive on the seated spine (UE convention: delta * base);
  - planted hands: two-bone IK pins both wrists on the mattress beside the hips, palms down (hold, breath, push-off);
  - reach: the reaching arm takes PickUp_Table's arm chain and is IK-warped so the hand closes on the clock.
Engine-free: `A` is an adapter with pose_at(clip, t), bones(p), lget/lset(p, bone) and wget/wset(p, bone) in
component space, with positions and (x, y, z, w) quaternions. build_anims.py passes AnimPose; the offline test passes GLB."""
import math
import wake_math as m
import slap_motion
import importlib
importlib.reload(slap_motion)

ARM_TOKENS = ("clavicle", "upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky", "metacarpal", "wrist")


def arm_bones(names, side):
    return [b for b in names if b.endswith("_" + side) and not b.startswith("ik_") and any(t in b for t in ARM_TOKENS)]


# Fan of each proximal finger about the palm normal at impact, degrees toward the thumb.
SPLAY_DEG = {"index_01": 7.5, "middle_01": 0.0, "ring_01": -5.0, "pinky_01": -9.0}  # on the rest fan (3.4, 6.0, 6.8 deg): about 11 deg apart, a dark gap from Cam_Hit (hit6: 7 deg read as a closed paddle)
TIP_CURL = (0.0, 3.0, 8.0)  # deg each phalanx (_01, _02, _03) bends below flat on the impact: a hand, not a ruler
THUMB_OUT, THUMB_DOWN = 25.0, 10.0  # the thumb lies alongside the index, turned out toward the thumb side and a little below the palm
HYPER = 0.08  # on the impact the fingers bend back past flat by about 4.5 deg


def splay_w(u, t_contact):
    """0 to 1: the fingers snap open and fan over the last 0.07 s before contact, then relax to the rest curl during the
    press and the sink (main, hit5: a slap on the impact frame, a natural hand in the pile)."""
    return min(m.smooth((u - (t_contact - .07)) / .07), 1.0 - m.smooth((u - (t_contact + .35)) / .45))


def flat_w(u, t_contact):
    """0 to 1: the fingers lie flat for the impact and the press, then drape again as the hand sinks into the pile."""
    return min(m.smooth((u - (t_contact - .06)) / .06), 1.0 - m.smooth((u - (t_contact + .35)) / .3))


def finger_bones(names, side):
    return [b for b in names if b.endswith("_" + side) and any(t in b for t in ("thumb", "index", "middle", "ring", "pinky"))]


def reach_peak(A, clip, side, length, fwd, step=1.0 / 30.0):
    """Clip time at which the hand is farthest forward of where it started: the grab (later it lifts to the chest)."""
    p0 = A.wget(A.pose_at(clip, 0.0), "hand_" + side)[0]
    best, t = (0.0, 0.0), 0.0
    while t <= length:
        d = m.dot(m.sub(A.wget(A.pose_at(clip, t), "hand_" + side)[0], p0), fwd)
        if d > best[0]:
            best = (d, t)
        t += step
    return best[1]


class Edge:
    def __init__(self, A, cfg):
        """cfg: clips {sit, pick, exit} with lengths; F, L, U (component forward/left/up); plant {l, r} wrist targets;
        clock (wrist target at the grab); reach_side ('l' or 'r'); spine bones; times; palm_out_deg."""
        self.A, self.c = A, cfg
        self.F, self.L, self.U = cfg["F"], cfg["L"], cfg["U"]
        p0 = A.pose_at(cfg["sit"], 0.0)
        self.names = A.bones(p0)
        self.relaxed = A.pose_at(cfg["pick"], 0.0)  # standing idle: relaxed fingers for the planted hands
        self.open_hand = cfg.get('open_hand_pose',self.relaxed)
        rs = cfg["reach_side"]
        self.rate_pick = cfg["pick_len"] / cfg["T_reach"]
        self.t_grab = reach_peak(A, cfg["pick"], rs, cfg["pick_len"], self.F) / self.rate_pick  # in reach-segment seconds
        self.warp = None  # wrist offset that lands the source grab on the clock, measured once
        self.slouch_deg = 0.0
        self.slouch_sign = self._slouch_sign()

    def _slouch_sign(self):
        """Which way about L flexes forward: the head must move along F."""
        p = self.seated(0.0)
        h0 = self.A.wget(p, self.c["spine"][-1])[0]
        self.slouch(p, 10.0, 1.0)
        return 1.0 if m.dot(m.sub(self.A.wget(p, self.c["spine"][-1])[0], h0), self.F) > 0 else -1.0

    def slouch(self, p, deg, sign=None):
        """Groggy posture: forward flexion spread evenly over the lower spine (shoulders drop toward the mattress)."""
        A = self.A
        chain = self.c["slouch_bones"]
        q = m.qaxis(self.L, (self.slouch_sign if sign is None else sign) * deg / len(chain))
        for b in chain:
            pos, wq = A.wget(p, b)
            A.wset(p, b, pos, m.qnorm(m.qmul(q, wq)))

    def auto_slouch(self, margin=0.97, step=1.0, limit=20.0):
        """Smallest flexion that brings both planted wrists within reach (arm nearly, not fully, straight)."""
        A = self.A
        deg = 0.0
        while deg <= limit:
            p = self.seated(0.0)
            self.slouch(p, deg)
            ok = True
            for side in ("l", "r"):
                s = A.wget(p, "upperarm_" + side)[0]
                arm = m.length(m.sub(A.wget(p, "lowerarm_" + side)[0], s)) +                     m.length(m.sub(A.wget(p, "hand_" + side)[0], A.wget(p, "lowerarm_" + side)[0]))
                ok = ok and m.length(m.sub(self.c["plant"][side], s)) <= margin * arm
            if ok:
                self.slouch_deg = deg
                return deg
            deg += step
        raise ValueError("planted hands out of reach even at %.0f deg of slouch: move the plant targets in" % limit)

    # ---- layers
    def spine_additive(self, p, tp, w):
        A = self.A
        ref, cur = A.pose_at(self.c["pick"], 0.0), A.pose_at(self.c["pick"], tp)
        for b in self.c["spine"]:
            delta = m.qmul(A.lget(cur, b)[1], m.qinv(A.lget(ref, b)[1]))
            delta = m.qslerp((0.0, 0.0, 0.0, 1.0), delta, w)
            pos, q = A.lget(p, b)
            A.lset(p, b, pos, m.qnorm(m.qmul(delta, q)))

    def chain_ik(self, p, a, b, c, target, pole, end_q=None):
        A = self.A
        s, qs = A.wget(p, a)
        e, _ = A.wget(p, b)
        w, _ = A.wget(p, c)
        q1, q2, _ = m.two_bone(s, e, w, target, pole)
        A.wset(p, a, s, m.qnorm(m.qmul(q1, qs)))
        e2, qe = A.wget(p, b)
        A.wset(p, b, e2, m.qnorm(m.qmul(q2, qe)))
        if end_q is not None:
            A.wset(p, c, A.wget(p, c)[0], end_q)

    def ik(self, p, side, target, pole, hand_q=None):
        self.chain_ik(p, "upperarm_" + side, "lowerarm_" + side, "hand_" + side, target, pole, hand_q)

    def raise_seat(self, p, w):
        """Lift the hips by seat_raise * w (the UAL chair is lower than the bed) and keep both feet where the clip put
        them with leg IK: flat soles, knees bending forward."""
        lift = self.c.get("seat_raise", 0.0) * w
        if lift <= 1e-3:
            return
        A = self.A
        feet = {sd: A.wget(p, "foot_" + sd) for sd in ("l", "r")}
        pos, q = A.lget(p, "pelvis")
        A.lset(p, "pelvis", m.add(pos, m.mul(self.U, lift)), q)
        for sd, (fpos, fq) in feet.items():
            knee = A.wget(p, "calf_" + sd)[0]
            self.chain_ik(p, "thigh_" + sd, "calf_" + sd, "foot_" + sd, fpos, m.add(knee, m.mul(self.F, 40.0)), fq)

    def plant(self, p, side):
        """Wrist on the mattress beside the hip, palm down, fingers forward and a little out, relaxed fingers."""
        A, F, L, U = self.A, self.F, self.L, self.U
        sgn = 1.0 if side == "l" else -1.0
        for b in finger_bones(self.names, side):
            pos, _ = A.lget(p, b)
            A.lset(p, b, pos, m.qslerp(A.lget(self.relaxed,b)[1],A.lget(self.open_hand,b)[1],.8))
        s, _ = A.wget(p, "upperarm_" + side)
        pole = m.add(s, m.add(m.mul(F, -40.0), m.add(m.mul(L, sgn * 25.0), m.mul(U, -10.0))))
        a = self.c.get("palm_out_deg", 20.0)
        f_d = m.norm(m.add(m.mul(F, m.cos_d(a)), m.mul(L, sgn * m.sin_d(a))))
        l_perp = m.norm(m.sub(L, m.mul(f_d, m.dot(L, f_d))))
        thumb_d = m.mul(l_perp, -sgn)  # palm down: the thumb points toward the body's midline
        self.ik(p, side, self.c["plant"][side], pole)
        hpos, hq = A.wget(p, "hand_" + side)
        f_c = m.sub(A.wget(p, "middle_01_" + side)[0], hpos)
        t_c = m.sub(A.wget(p, "index_01_" + side)[0], A.wget(p, "pinky_01_" + side)[0])
        A.wset(p, "hand_" + side, hpos, m.qnorm(m.qmul(m.align(f_c, t_c, f_d, thumb_d), hq)))

    def reach(self, p, u):
        """Reach arm: PickUp_Table's arm chain on the (additive) seated torso, wrist warped onto the clock."""
        A, side = self.A, self.c["reach_side"]
        src = A.pose_at(self.c["pick"], u * self.rate_pick)
        for b in arm_bones(self.names, side):
            pos, _ = A.lget(p, b)
            A.lset(p, b, pos, A.lget(src, b)[1])
        if self.warp is None:
            return
        g = self.t_grab
        w = m.smooth(u / g) if u <= g else (1.0 if u <= g + 0.15 else 1.0 - m.smooth((u - g - 0.15) / 0.45))
        if w <= 1e-3:
            return
        s = A.wget(p, "upperarm_" + side)[0]
        e = A.wget(p, "lowerarm_" + side)[0]
        wr = A.wget(p, "hand_" + side)[0]
        pole = m.add(e, m.mul(m.sub(e, m.lerp(s, wr, 0.5)), 2.0))  # keep the source elbow plane
        self.ik(p, side, m.add(wr, m.mul(self.warp, w)), pole, A.wget(p, "hand_" + side)[1])

    def slap(self, p, u, planted):
        """Snooze slap (cfg["slap"]): the hand arcs up over the clock, slams palm-down on its lid at t_contact (an
        accelerating drop, so the contact frame is crisp), presses as the clock caves in, and the caller blends the arm
        back to the mattress. Two-bone IK on the wrist; the torso leans toward the clock and the head tracks it."""
        A, F, L, U, S = self.A, self.F, self.L, self.U, self.c["slap"]
        side = self.c["reach_side"]
        sgn = 1.0 if side == "l" else -1.0
        top = S["top"]
        start = A.wget(planted, "hand_" + side)[0]
        # The motion's lean curve is independent of arm proportions.
        _, _, lean_w = slap_motion.sample(u, start, top, F, U, self.c["T_reach"], S["t_contact"])
        sh0 = A.wget(p, "upperarm_" + side)[0]
        d = m.sub(top, sh0)
        d = m.norm((d[0], d[1], 0.0))
        if lean_w > 1e-3:  # lean over: spine_02/03 turn U toward the clock, then the head looks at the lid
            lq = m.qaxis(m.norm(m.cross(U, d)), S["lean_deg"] * lean_w * 0.5)
            for b in ("spine_02", "spine_03"):
                pos, wq = A.wget(p, b)
                A.wset(p, b, pos, m.qnorm(m.qmul(lq, wq)))
            hpos, hq = A.wget(p, "head")
            look = m.qslerp((0.0, 0.0, 0.0, 1.0), m.from_to(m.qrot(hq, S["face_local"]), m.norm(m.sub(top, hpos))),
                            S["look_w"] * lean_w)
            for b, frac in (("neck_01", 0.4), ("neck_02", 0.3), ("head", 0.3)):
                pos, wq = A.wget(p, b)
                A.wset(p, b, pos, m.qnorm(m.qmul(m.qslerp((0.0, 0.0, 0.0, 1.0), look, frac), wq)))
        sh = A.wget(p, "upperarm_" + side)[0]
        f_d = m.norm((top[0] - sh[0], top[1] - sh[1], 0.0))
        wrist_c = m.add(m.sub(top, m.mul(f_d, S["palm_off"])), m.mul(U, S["palm_h"]))
        wrist_c = m.add(wrist_c,S.get('retarget_offset',(0,0,0)))
        gesture_pole = m.add(sh, m.add(m.mul(L, sgn * 25.0), m.add(m.mul(U, -24.0), m.mul(F, -25.0))))
        # The palm continues the forearm; solve its wrist offset in that same frame.
        for _ in range(6):
            self.ik(p, side, wrist_c, gesture_pole)
            forearm = m.sub(A.wget(p, "hand_" + side)[0], A.wget(p, "lowerarm_" + side)[0])
            f_d = m.norm(m.sub(forearm, m.mul(U, m.dot(forearm, U))))
            wrist_c = m.add(m.add(m.sub(top, m.mul(f_d, S["palm_off"])), m.mul(U, S["palm_h"])),
                            S.get('retarget_offset',(0,0,0)))
        pos, flex, _ = slap_motion.sample(u, start, wrist_c, f_d, U, self.c["T_reach"], S["t_contact"])
        orient_w = min(m.smooth(u / .35), 1.0-m.smooth((u-(self.c["T_reach"]-.7))/.7))
        # Keep the elbow below the shoulder through gathering and contact.
        tucked_pole = m.add(sh, m.add(m.mul(L, sgn * 12.0), m.add(m.mul(U, -45.0), m.mul(F, -10.0))))
        strike_w = min(m.smooth((u-1.05)/.45), 1.0-m.smooth((u-2.72)/.38))
        motion_pole = m.lerp(tucked_pole, gesture_pole, strike_w)
        pole = m.lerp(A.wget(planted, "lowerarm_" + side)[0], motion_pole, orient_w)
        self.ik(p, side, pos, pole)
        hpos, hq = A.wget(p, "hand_" + side)
        forearm = m.norm(m.sub(hpos, A.wget(p, "lowerarm_" + side)[0]))
        flat = m.norm(m.sub(forearm, m.mul(U, m.dot(forearm, U))))
        contact_w = min(m.smooth((u-1.25)/.25), 1.0-m.smooth((u-2.72)/.38))
        f_d = m.norm(m.lerp(forearm, flat, contact_w * .55))
        thumb_d = m.mul(m.norm(m.cross(U, f_d)), sgn)
        f_c = m.sub(A.wget(p, "middle_01_" + side)[0], hpos)
        t_c = m.sub(A.wget(p, "index_01_" + side)[0], A.wget(p, "pinky_01_" + side)[0])
        palm_q = m.qnorm(m.qmul(m.align(f_c, t_c, f_d, thumb_d), hq))
        palm_q = m.qnorm(m.qmul(m.qaxis(m.cross(U, f_d), flex * .3), palm_q))
        # Return to the exact planted hand frame, not a blend of entire arm chains.
        A.wset(p, "hand_" + side, hpos, m.qslerp(A.wget(planted, "hand_" + side)[1], palm_q, orient_w))
        w = splay_w(u, S["t_contact"])
        if w > 1e-3:  # positive turns about the palm normal swing a finger toward the thumb (cross(U, f_d) = sgn * thumb_d)
            n = U  # the palm is flat on the lid by then
            for root, deg in SPLAY_DEG.items():
                b = root + "_" + side
                if b in self.names and deg:
                    pos, wq = A.wget(p, b)
                    A.wset(p, b, pos, m.qnorm(m.qmul(m.qaxis(n, sgn * deg * w), wq)))
        f = flat_w(u, S["t_contact"])
        if f > 1e-3:  # a flat slap: lay each phalanx onto the palm plane (axis-free, so any skeleton's finger frames work)
            for d in ("index", "middle", "ring", "pinky"):
                chain = [b for b in (d + "_01_" + side, d + "_02_" + side, d + "_03_" + side) if b in self.names]
                for i, b in enumerate(chain):
                    pos, wq = A.wget(p, b)
                    nxt = A.wget(p, chain[i + 1])[0] if i + 1 < len(chain) else m.add(pos, m.sub(pos, A.wget(p, chain[i - 1])[0]))
                    v = m.norm(m.sub(nxt, pos))
                    flat = m.sub(v, m.mul(U, m.dot(v, U)))
                    tilt = (HYPER if i == 0 else 0.0) - math.tan(math.radians(TIP_CURL[i]))  # the knuckle bends back, the tips curl
                    flat = m.add(flat, m.mul(U, tilt * m.length(flat) * splay_w(u, S["t_contact"])))
                    if m.length(flat) > 1e-3:
                        turn = m.qslerp((0.0, 0.0, 0.0, 1.0), m.from_to(v, m.norm(flat)), f)
                        A.wset(p, b, pos, m.qnorm(m.qmul(turn, wq)))

        tw = min(m.smooth((u - (S["t_contact"] - .1)) / .1), 1.0 - m.smooth((u - 2.72) / .38))
        thumbs = [b for b in ("thumb_01_" + side, "thumb_02_" + side, "thumb_03_" + side) if b in self.names]
        if tw > 1e-3 and len(thumbs) == 3:  # the thumb alongside the index, never hanging below the palm (hit6)
            i1, i2 = A.wget(p, "index_01_" + side)[0], A.wget(p, "index_02_" + side)[0]
            idx = m.norm(m.sub(m.sub(i2, i1), m.mul(U, m.dot(m.sub(i2, i1), U))))
            side_d = m.norm(m.sub(m.mul(thumb_d, 1.0), m.mul(idx, m.dot(thumb_d, idx))))
            a, b_ = math.radians(THUMB_OUT), math.radians(THUMB_DOWN)
            want = m.norm(m.sub(m.add(m.mul(idx, math.cos(a)), m.mul(side_d, math.sin(a))), m.mul(U, math.tan(b_))))
            for i, b in enumerate(thumbs):
                pos, wq = A.wget(p, b)
                nxt = A.wget(p, thumbs[i + 1])[0] if i + 1 < 3 else m.add(pos, m.sub(pos, A.wget(p, thumbs[i - 1])[0]))
                turn = m.qslerp((0.0, 0.0, 0.0, 1.0), m.from_to(m.norm(m.sub(nxt, pos)), want), tw)
                A.wset(p, b, pos, m.qnorm(m.qmul(turn, wq)))

    def palm_point(self, p):
        """Component-space centre of the reach hand's palm surface (where it meets the lid)."""
        A, side, S = self.A, self.c["reach_side"], self.c["slap"]
        h = A.wget(p, "hand_" + side)[0]
        f = m.sub(A.wget(p, "middle_01_" + side)[0], h)
        return m.sub(m.add(h, m.mul(f, S["palm_off"] / max(1e-3, m.length(f)))), m.mul(self.U, S["palm_h"]))

    def source_grab(self):
        """Component-space wrist position of the unwarped mocap grab (placement aims the clock here)."""
        warp, self.warp = self.warp, None
        p = self.seated(self.c["T_hold"] + self.t_grab, True)
        self.spine_additive(p, self.t_grab * self.rate_pick, 1.0)
        self.reach(p, self.t_grab)
        self.warp = warp
        return self.A.wget(p, "hand_" + self.c["reach_side"])[0]

    def measure_warp(self):
        self.warp = m.sub(self.c["clock"], self.source_grab())
        return self.warp

    # ---- timeline
    def seated(self, t, slouch=False):
        p = self.A.pose_at(self.c["sit"], t % self.c["sit_len"])
        self.raise_seat(p, 1.0)
        if slouch and self.slouch_deg:
            self.slouch(p, self.slouch_deg)
        return p

    def blend_arm(self, dst, src, side, w):
        """dst arm chain = slerp(src, dst, w) in local space (dst holds the layered solution)."""
        A = self.A
        for b in arm_bones(self.names, side):
            pos, qd = A.lget(dst, b)
            A.lset(dst, b, pos, m.qslerp(A.lget(src, b)[1], qd, w))

    def frame(self, t):
        c, A = self.c, self.A
        T1 = c["T_hold"]
        T2 = T1 + c["T_reach"]
        T3 = T2 + c["T_breath"]
        rs, other = c["reach_side"], ("r" if c["reach_side"] == "l" else "l")
        if t < T1 or T2 <= t < T3:
            p = self.seated(t, True)
            self.plant(p, "l")
            self.plant(p, "r")
            return p
        if t < T2 and c.get("slap"):
            u, S = t - T1, c["slap"]
            p = self.seated(t, True)
            planted = self.seated(t, True)
            self.plant(planted, rs)
            for b in finger_bones(self.names, rs):
                pos, _ = A.lget(p, b)
                opening=min(m.smooth(u/.55),1-m.smooth((u-(c['T_reach']-.55))/.55))
                A.lset(p,b,pos,m.qslerp(A.lget(planted,b)[1],A.lget(self.open_hand,b)[1],opening * (.65 + .35 * splay_w(u, S['t_contact']))))
            self.slap(p, u, planted)
            self.plant(p, other)
            return p
        if t < T2:
            u = t - T1
            w_io = min(m.smooth(u / 0.3), m.smooth((T2 - t) / 0.4))
            p = self.seated(t, True)
            self.spine_additive(p, u * self.rate_pick, w_io)
            planted = self.seated(t, True)
            self.spine_additive(planted, u * self.rate_pick, w_io)
            self.plant(planted, rs)
            self.reach(p, u)
            self.blend_arm(p, planted, rs, w_io)
            self.plant(p, other)
            return p
        u = (t - T3) * c["exit_rate"]  # stand: hands push off the mattress until the hips lift
        p = A.pose_at(c["exit"], min(u, c["exit_len"]))
        self.raise_seat(p, 1.0 - m.smooth((u - 0.3) / 0.4))  # the lift fades out as the hips leave the bed
        w = 1.0 - m.smooth((u - c["release"][0]) / (c["release"][1] - c["release"][0]))
        if w > 1e-3 and self.slouch_deg:
            self.slouch(p, self.slouch_deg * w)
        if w > 1e-3:
            src = A.pose_at(c["exit"], min(u, c["exit_len"]))
            self.raise_seat(src, 1.0 - m.smooth((u - 0.3) / 0.4))
            for side in ("l", "r"):
                self.plant(p, side)
                self.blend_arm(p, src, side, w)
        return p

    def duration(self):
        c = self.c
        return c["T_hold"] + c["T_reach"] + c["T_breath"] + c["exit_len"] / c["exit_rate"]
