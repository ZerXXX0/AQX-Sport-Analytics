import math
import pytest
from shot_geometry import shot_value_at


@pytest.mark.parametrize('x,y,expected', [
    (0, 0, 2), (0, 15, 2), (0, 23.75, 2), (0, 24, 3),
    (22, 0, 2), (-22, 0, 2), (22.5, 0, 3), (-22.5, 0, 3),
    (21.5, 0, 2), (23, -4, 3), (0, -4, 2),
    (22, math.sqrt(23.75**2 - 22**2), 2),
    (21, 12, 3), (20, 12, 2),
])
def test_three_point_geometry(x, y, expected):
    assert shot_value_at(x, y) == expected


@pytest.mark.parametrize('x,y', [(float('nan'), 0), (0, float('inf')), (25, 0), (0, -5.25), (0, 41.75)])
def test_invalid_locations(x, y):
    with pytest.raises(ValueError):
        shot_value_at(x, y)


def test_simulator_uses_automatic_value():
    from streamlit.testing.v1 import AppTest
    from core import ROOT
    at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=90).run()
    assert not at.exception
    assert not any(s.label == 'Shot value' for s in at.selectbox)
    x_slider = next(s for s in at.slider if s.label.startswith('Width from basket'))
    y_slider = next(s for s in at.slider if s.label.startswith('Length from basket'))
    x_slider.set_value(23.0)
    y_slider.set_value(0.0)
    at.run()
    assert any('Shot value: 3 points' in c.value for c in at.caption)
    at.button[0].click().run()
    assert not at.exception
    probability = next(m.value for m in at.metric if m.label == 'Make Probability')
    expected = float(next(m.value for m in at.metric if m.label == 'Expected Pts/Att'))
    assert abs(expected - float(probability.rstrip('%'))/100*3) < .0021
    next(s for s in at.slider if s.label.startswith('Width from basket')).set_value(0.0).run()
    assert any('Shot value: 2 points' in c.value for c in at.caption)
