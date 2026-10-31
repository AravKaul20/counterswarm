import numpy as np
from sim.world import los_clear

BOX = (np.array([0.0, 0.0, 0.0]), np.array([10.0, 10.0, 10.0]))


def test_segment_through_box_is_blocked():
    assert not los_clear(np.array([-5.0, 5.0, 5.0]), np.array([15.0, 5.0, 5.0]), [BOX])


def test_segment_over_box_is_clear():
    assert los_clear(np.array([-5.0, 5.0, 12.0]), np.array([15.0, 5.0, 12.0]), [BOX])


def test_segment_stopping_short_of_box_is_clear():
    assert los_clear(np.array([-20.0, 5.0, 5.0]), np.array([-1.0, 5.0, 5.0]), [BOX])


def test_axis_parallel_segment_beside_box_is_clear():
    # zero direction component along y and z, outside the box's y slab
    assert los_clear(np.array([-5.0, 20.0, 5.0]), np.array([15.0, 20.0, 5.0]), [BOX])


def test_diagonal_segment_clipping_corner_is_blocked():
    assert not los_clear(np.array([-1.0, 5.0, 5.0]), np.array([5.0, -1.0, 5.0]), [BOX])


def test_no_boxes_is_clear():
    assert los_clear(np.zeros(3), np.ones(3), [])
