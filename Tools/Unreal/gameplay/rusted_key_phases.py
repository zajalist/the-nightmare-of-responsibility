"""Authored key resistance stages, consumed by the Blueprint graph builder.

Each stage is (minimum angle, maximum angle, degrees/second, must ease back).
Full input takes 11.13 seconds plus the kneeling/contact and release animations.
Holding turn forever cannot pass the bind; idle input never advances a stage.
"""
KEY_PHASES = ((0.0, 18.0, 6.0, False),
              (18.0, 42.0, 6.0, False),
              (30.0, 42.0, 12.0, True),
              (30.0, 55.0, 8.0, False))
KEY_HINTS = ('Find the catch. Turn slowly.',
             'It is moving. Keep gentle pressure.',
             'It binds here. Ease back until it loosens.',
             'Try again. Keep the pressure steady.')
